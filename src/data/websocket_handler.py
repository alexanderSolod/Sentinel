"""
WebSocket Handler for Streaming Polymarket Trade Events
Adapted from polymarket-insider-tracker (MIT License)

Provides:
- Real-time trade streaming via WebSocket
- Automatic reconnection with exponential backoff
- Event filtering by market/event
- Connection state management
"""
import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import websockets, provide fallback message if not available
try:
    import websockets
    from websockets.asyncio.client import ClientConnection
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    ClientConnection = None
    logger.warning("websockets not installed - real-time streaming unavailable")

# Constants (from polymarket-insider-tracker)
DEFAULT_WS_HOST = "wss://ws-live-data.polymarket.com"
DEFAULT_PING_INTERVAL = 30  # seconds
DEFAULT_MAX_RECONNECT_DELAY = 30  # seconds
DEFAULT_INITIAL_RECONNECT_DELAY = 1  # seconds


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class StreamStats:
    """Statistics about the trade stream."""
    trades_received: int = 0
    reconnect_count: int = 0
    last_trade_time: Optional[float] = None
    connected_since: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class TradeEvent:
    """Trade event from WebSocket stream."""
    trade_id: str
    market_id: str
    market_slug: str
    wallet_address: str
    side: str  # "buy" or "sell"
    outcome: str  # "yes" or "no"
    price: Decimal
    size: Decimal
    notional_value: Decimal
    timestamp: datetime
    raw_data: dict = field(default_factory=dict)

    @classmethod
    def from_websocket_message(cls, payload: dict) -> "TradeEvent":
        """Parse a trade event from WebSocket payload."""
        timestamp_ms = payload.get("timestamp", 0)
        if timestamp_ms:
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        return cls(
            trade_id=str(payload.get("id", "")),
            market_id=payload.get("market_id", payload.get("condition_id", "")),
            market_slug=payload.get("market_slug", ""),
            wallet_address=payload.get("trader", payload.get("wallet_address", "")).lower(),
            side=payload.get("side", "buy").lower(),
            outcome=payload.get("outcome", "").lower(),
            price=Decimal(str(payload.get("price", 0))),
            size=Decimal(str(payload.get("size", 0))),
            notional_value=Decimal(str(payload.get("notional_value", payload.get("size", 0)))),
            timestamp=timestamp,
            raw_data=payload,
        )


class TradeStreamError(Exception):
    """Base exception for trade stream errors."""
    pass


class WebSocketConnectionError(TradeStreamError):
    """Raised when connection to WebSocket fails."""
    pass


# Type aliases
TradeCallback = Callable[[TradeEvent], Awaitable[None]]
StateCallback = Callable[[ConnectionState], Awaitable[None]]


class TradeStreamHandler:
    """
    WebSocket client for streaming Polymarket trade events.

    Adapted from polymarket-insider-tracker (MIT License).

    This handler maintains a persistent connection to Polymarket's real-time
    trade feed, automatically reconnecting on disconnection with exponential
    backoff.

    Example:
        >>> async def on_trade(trade: TradeEvent):
        ...     print(f"Trade: {trade.side} {trade.size} @ {trade.price}")
        ...
        >>> handler = TradeStreamHandler(on_trade=on_trade)
        >>> await handler.start()  # Blocks until stop() is called
    """

    def __init__(
        self,
        on_trade: TradeCallback,
        *,
        host: str = DEFAULT_WS_HOST,
        on_state_change: Optional[StateCallback] = None,
        ping_interval: int = DEFAULT_PING_INTERVAL,
        max_reconnect_delay: int = DEFAULT_MAX_RECONNECT_DELAY,
        initial_reconnect_delay: int = DEFAULT_INITIAL_RECONNECT_DELAY,
        event_filter: Optional[str] = None,
        market_filter: Optional[str] = None,
    ) -> None:
        """
        Initialize the trade stream handler.

        Args:
            on_trade: Async callback invoked for each trade event.
            host: WebSocket endpoint URL.
            on_state_change: Optional callback for connection state changes.
            ping_interval: Seconds between heartbeat pings.
            max_reconnect_delay: Maximum delay between reconnection attempts.
            initial_reconnect_delay: Initial delay for reconnection backoff.
            event_filter: Optional event slug to filter trades by event.
            market_filter: Optional market slug to filter trades by market.
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package required for TradeStreamHandler")

        self._on_trade = on_trade
        self._on_state_change = on_state_change
        self._host = host
        self._ping_interval = ping_interval
        self._max_reconnect_delay = max_reconnect_delay
        self._initial_reconnect_delay = initial_reconnect_delay
        self._event_filter = event_filter
        self._market_filter = market_filter

        self._state = ConnectionState.DISCONNECTED
        self._stats = StreamStats()
        self._ws: Optional[ClientConnection] = None
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def stats(self) -> StreamStats:
        """Stream statistics."""
        return self._stats

    async def _set_state(self, new_state: ConnectionState) -> None:
        """Update state and notify callback."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.info("Connection state: %s -> %s", old_state.value, new_state.value)

            if self._on_state_change:
                try:
                    await self._on_state_change(new_state)
                except Exception as e:
                    logger.error("Error in state change callback: %s", e)

    def _build_subscription_message(self) -> dict[str, Any]:
        """Build the WebSocket subscription message."""
        subscription: dict[str, Any] = {
            "topic": "activity",
            "type": "trades",
        }

        # Add filters if specified
        if self._event_filter:
            subscription["filters"] = json.dumps({"event_slug": self._event_filter})
        elif self._market_filter:
            subscription["filters"] = json.dumps({"market_slug": self._market_filter})

        return {"subscriptions": [subscription]}

    async def _connect(self) -> ClientConnection:
        """Establish WebSocket connection."""
        await self._set_state(ConnectionState.CONNECTING)

        try:
            ws = await websockets.connect(
                self._host,
                ping_interval=self._ping_interval,
                ping_timeout=self._ping_interval * 2,
            )

            # Send subscription message
            subscribe_msg = self._build_subscription_message()
            await ws.send(json.dumps(subscribe_msg))

            logger.info("Connected to %s and subscribed to trades", self._host)
            await self._set_state(ConnectionState.CONNECTED)
            self._stats.connected_since = time.time()

            return ws

        except Exception as e:
            logger.error("Failed to connect: %s", e)
            self._stats.last_error = str(e)
            raise WebSocketConnectionError(f"Failed to connect to {self._host}: {e}") from e

    async def _handle_message(self, message: str) -> None:
        """Parse and process an incoming WebSocket message."""
        try:
            data = json.loads(message)

            # Check if this is a trade message
            topic = data.get("topic")
            msg_type = data.get("type")

            if topic == "activity" and msg_type == "trades":
                payload = data.get("payload", {})
                trade = TradeEvent.from_websocket_message(payload)

                self._stats.trades_received += 1
                self._stats.last_trade_time = time.time()

                logger.debug(
                    "Trade: %s %s @ %s on %s",
                    trade.side,
                    trade.size,
                    trade.price,
                    trade.market_slug,
                )

                try:
                    await self._on_trade(trade)
                except Exception as e:
                    logger.error("Error in trade callback: %s", e)

            else:
                # Log other message types for debugging
                logger.debug("Received message: topic=%s type=%s", topic, msg_type)

        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON message: %s", e)
        except Exception as e:
            logger.error("Error processing message: %s", e)

    async def _listen(self, ws: ClientConnection) -> None:
        """Listen for messages on the WebSocket."""
        try:
            async for message in ws:
                if not self._running:
                    break

                if isinstance(message, str):
                    await self._handle_message(message)
                else:
                    logger.debug("Received binary message (%d bytes)", len(message))

        except websockets.ConnectionClosed as e:
            logger.warning("Connection closed: %s", e)
            raise
        except Exception as e:
            logger.error("Error in message loop: %s", e)
            raise

    async def _reconnect_loop(self) -> None:
        """Handle reconnection with exponential backoff."""
        delay = self._initial_reconnect_delay

        while self._running:
            try:
                await self._set_state(ConnectionState.RECONNECTING)

                logger.info("Reconnecting in %.1f seconds...", delay)
                await asyncio.sleep(delay)

                if not self._running:
                    break

                self._ws = await self._connect()
                self._stats.reconnect_count += 1
                delay = self._initial_reconnect_delay  # Reset delay on success
                return

            except Exception as e:
                logger.error("Reconnection failed: %s", e)
                self._stats.last_error = str(e)

                # Exponential backoff
                delay = min(delay * 2, self._max_reconnect_delay)

    async def start(self) -> None:
        """
        Connect and begin streaming trades.

        This method blocks until stop() is called. It automatically
        handles reconnection on disconnection.
        """
        if self._running:
            logger.warning("Handler already running")
            return

        self._running = True
        self._stop_event = asyncio.Event()

        try:
            # Initial connection
            self._ws = await self._connect()

            # Main loop
            while self._running:
                try:
                    await self._listen(self._ws)
                except Exception as e:
                    if not self._running:
                        break

                    logger.warning("Connection lost: %s", e)
                    await self._set_state(ConnectionState.DISCONNECTED)

                    # Attempt reconnection
                    await self._reconnect_loop()

                    if not self._running or self._ws is None:
                        break

        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Gracefully disconnect from the WebSocket."""
        if not self._running:
            return

        logger.info("Stopping trade stream handler...")
        self._running = False

        if self._stop_event:
            self._stop_event.set()

        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug("Error closing WebSocket: %s", e)
            finally:
                self._ws = None

        await self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Trade stream handler stopped")

    async def __aenter__(self) -> "TradeStreamHandler":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()


# Simplified synchronous wrapper for testing
class MockTradeStream:
    """Mock trade stream for testing without WebSocket connection."""

    def __init__(self):
        self.trades: list[TradeEvent] = []
        self._callbacks: list[TradeCallback] = []

    def add_callback(self, callback: TradeCallback):
        """Add a trade callback."""
        self._callbacks.append(callback)

    async def emit_trade(self, trade: TradeEvent):
        """Emit a trade to all callbacks."""
        self.trades.append(trade)
        for callback in self._callbacks:
            await callback(trade)

    def create_mock_trade(
        self,
        market_id: str = "test-market",
        wallet: str = "0x" + "a" * 40,
        side: str = "buy",
        price: float = 0.65,
        size: float = 1000,
    ) -> TradeEvent:
        """Create a mock trade event."""
        return TradeEvent(
            trade_id=f"trade-{len(self.trades)}",
            market_id=market_id,
            market_slug="test-market-slug",
            wallet_address=wallet.lower(),
            side=side,
            outcome="yes" if side == "buy" else "no",
            price=Decimal(str(price)),
            size=Decimal(str(size)),
            notional_value=Decimal(str(size)),
            timestamp=datetime.now(timezone.utc),
        )


if __name__ == "__main__":
    print("Testing WebSocket Handler...")

    if not WEBSOCKETS_AVAILABLE:
        print("websockets not installed - testing mock stream only")

        async def test_mock():
            mock = MockTradeStream()

            async def on_trade(trade: TradeEvent):
                print(f"  Trade: {trade.side} {trade.size} @ {trade.price}")

            mock.add_callback(on_trade)

            # Emit some mock trades
            for i in range(3):
                trade = mock.create_mock_trade(
                    wallet=f"0x{i:040x}",
                    price=0.5 + i * 0.1,
                    size=1000 * (i + 1),
                )
                await mock.emit_trade(trade)

            print(f"  Total trades: {len(mock.trades)}")

        asyncio.run(test_mock())
    else:
        print("websockets available - can connect to real stream")
        print("Use: handler = TradeStreamHandler(on_trade=callback)")
        print("     await handler.start()")
