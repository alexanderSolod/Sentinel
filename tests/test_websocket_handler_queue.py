import asyncio
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from src.data.websocket_handler import TradeEvent, TradeStreamHandler, WEBSOCKETS_AVAILABLE


@unittest.skipUnless(WEBSOCKETS_AVAILABLE, "websockets package is required")
class TradeStreamHandlerQueueTests(unittest.IsolatedAsyncioTestCase):
    def _make_trade(self, trade_id: str) -> TradeEvent:
        return TradeEvent(
            trade_id=trade_id,
            market_id="market-1",
            market_slug="market-1",
            wallet_address="0x" + "a" * 40,
            side="buy",
            outcome="yes",
            price=Decimal("0.55"),
            size=Decimal("1000"),
            notional_value=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )

    async def test_queue_worker_processes_enqueued_trade(self) -> None:
        processed: list[str] = []

        async def on_trade(trade: TradeEvent) -> None:
            await asyncio.sleep(0.01)
            processed.append(trade.trade_id)

        handler = TradeStreamHandler(
            on_trade=on_trade,
            worker_concurrency=2,
            max_queue_size=8,
            callback_timeout_seconds=1.0,
        )
        handler._running = True
        await handler._start_workers()

        await handler._enqueue_trade(self._make_trade("t-1"))
        await asyncio.wait_for(handler._trade_queue.join(), timeout=1.0)  # type: ignore[arg-type]
        await handler._stop_workers()

        self.assertEqual(processed, ["t-1"])
        self.assertEqual(handler.stats.trades_enqueued, 1)
        self.assertEqual(handler.stats.trades_processed, 1)
        self.assertEqual(handler.stats.trades_dropped, 0)

    async def test_backpressure_drop_when_queue_full(self) -> None:
        async def on_trade(_: TradeEvent) -> None:
            await asyncio.sleep(0.05)

        handler = TradeStreamHandler(
            on_trade=on_trade,
            worker_concurrency=1,
            max_queue_size=1,
            drop_on_backpressure=True,
        )
        handler._trade_queue = asyncio.Queue(maxsize=1)

        await handler._enqueue_trade(self._make_trade("t-1"))
        await handler._enqueue_trade(self._make_trade("t-2"))

        self.assertEqual(handler.stats.trades_enqueued, 1)
        self.assertEqual(handler.stats.trades_dropped, 1)


if __name__ == "__main__":
    unittest.main()
