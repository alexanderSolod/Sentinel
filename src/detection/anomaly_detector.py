"""
Anomaly Detection Engine
Adapted from polymarket-insider-tracker (MIT License)

Detects:
- Volume spikes (>3x rolling baseline)
- Price jumps (>15 percentage point moves)
- Fresh wallet patterns
- Coordinated cluster behavior
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import statistics

logger = logging.getLogger(__name__)

# Detection thresholds
VOLUME_SPIKE_THRESHOLD = 3.0  # 3x baseline triggers anomaly
PRICE_JUMP_THRESHOLD = 0.15  # 15 percentage point move
Z_SCORE_THRESHOLD = 2.0  # Standard deviations from mean

# Fresh wallet thresholds (from polymarket-insider-tracker)
DEFAULT_MAX_NONCE = 5  # Max transactions to be considered fresh
DEFAULT_MAX_AGE_HOURS = 48.0  # Max age to be considered fresh
DEFAULT_MIN_TRADE_SIZE = Decimal("1000")  # $1,000 minimum

# Confidence scoring constants
BASE_CONFIDENCE = 0.5
BRAND_NEW_BONUS = 0.2  # nonce == 0
VERY_YOUNG_BONUS = 0.1  # age < 2 hours
LARGE_TRADE_BONUS = 0.1  # trade size > $10,000
LARGE_TRADE_THRESHOLD = Decimal("10000")


@dataclass
class AnomalySignal:
    """Base signal for any detected anomaly."""
    signal_type: str
    market_id: str
    timestamp: datetime
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VolumeSpike(AnomalySignal):
    """Volume spike detection signal."""
    volume_24h: float = 0.0
    baseline_volume: float = 0.0
    spike_ratio: float = 0.0
    z_score: float = 0.0


@dataclass
class PriceJump(AnomalySignal):
    """Price jump detection signal."""
    price_before: float = 0.0
    price_after: float = 0.0
    price_change: float = 0.0
    direction: str = "UP"  # UP or DOWN


@dataclass
class FreshWalletSignal(AnomalySignal):
    """Fresh wallet detection signal (adapted from polymarket-insider-tracker)."""
    wallet_address: str = ""
    wallet_age_hours: Optional[float] = None
    wallet_nonce: int = 0
    trade_size: Decimal = Decimal("0")
    factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class WalletProfile:
    """Wallet profile for analysis."""
    address: str
    first_seen: Optional[datetime] = None
    nonce: int = 0
    age_hours: Optional[float] = None
    is_fresh: bool = False
    total_volume: Decimal = Decimal("0")
    trade_count: int = 0
    win_rate: Optional[float] = None


class VolumeDetector:
    """Detects volume spikes in market activity."""

    def __init__(
        self,
        spike_threshold: float = VOLUME_SPIKE_THRESHOLD,
        z_score_threshold: float = Z_SCORE_THRESHOLD,
    ):
        self.spike_threshold = spike_threshold
        self.z_score_threshold = z_score_threshold
        self._volume_history: Dict[str, List[float]] = {}

    def record_volume(self, market_id: str, volume: float):
        """Record volume observation for baseline calculation."""
        if market_id not in self._volume_history:
            self._volume_history[market_id] = []
        self._volume_history[market_id].append(volume)
        # Keep last 30 observations
        if len(self._volume_history[market_id]) > 30:
            self._volume_history[market_id] = self._volume_history[market_id][-30:]

    def detect(
        self,
        market_id: str,
        current_volume: float,
        market_name: str = ""
    ) -> Optional[VolumeSpike]:
        """
        Detect if current volume represents a spike.

        Args:
            market_id: Market identifier
            current_volume: Current 24h volume
            market_name: Optional market name for logging

        Returns:
            VolumeSpike signal if detected, None otherwise
        """
        history = self._volume_history.get(market_id, [])

        if len(history) < 3:
            # Not enough data for baseline
            self.record_volume(market_id, current_volume)
            return None

        # Calculate baseline and z-score
        mean_volume = statistics.mean(history)
        if mean_volume == 0:
            return None

        stdev = statistics.stdev(history) if len(history) > 1 else mean_volume * 0.5
        if stdev == 0:
            stdev = mean_volume * 0.1

        spike_ratio = current_volume / mean_volume
        z_score = (current_volume - mean_volume) / stdev

        # Record current observation
        self.record_volume(market_id, current_volume)

        # Check thresholds
        if spike_ratio >= self.spike_threshold or z_score >= self.z_score_threshold:
            confidence = min(0.5 + (z_score / 10), 0.95)

            logger.info(
                "Volume spike detected: market=%s, ratio=%.1fx, z=%.1f",
                market_id[:10],
                spike_ratio,
                z_score,
            )

            return VolumeSpike(
                signal_type="volume_spike",
                market_id=market_id,
                timestamp=datetime.now(),
                confidence=confidence,
                details={"market_name": market_name},
                volume_24h=current_volume,
                baseline_volume=mean_volume,
                spike_ratio=spike_ratio,
                z_score=z_score,
            )

        return None


class PriceDetector:
    """Detects significant price movements."""

    def __init__(self, jump_threshold: float = PRICE_JUMP_THRESHOLD):
        self.jump_threshold = jump_threshold
        self._price_history: Dict[str, List[float]] = {}

    def record_price(self, market_id: str, price: float):
        """Record price observation."""
        if market_id not in self._price_history:
            self._price_history[market_id] = []
        self._price_history[market_id].append(price)
        if len(self._price_history[market_id]) > 100:
            self._price_history[market_id] = self._price_history[market_id][-100:]

    def detect(
        self,
        market_id: str,
        current_price: float,
        market_name: str = ""
    ) -> Optional[PriceJump]:
        """
        Detect significant price jump.

        Args:
            market_id: Market identifier
            current_price: Current price (0-1)
            market_name: Optional market name

        Returns:
            PriceJump signal if detected, None otherwise
        """
        history = self._price_history.get(market_id, [])

        if not history:
            self.record_price(market_id, current_price)
            return None

        previous_price = history[-1]
        price_change = current_price - previous_price

        self.record_price(market_id, current_price)

        if abs(price_change) >= self.jump_threshold:
            direction = "UP" if price_change > 0 else "DOWN"
            confidence = min(0.5 + abs(price_change), 0.95)

            logger.info(
                "Price jump detected: market=%s, change=%.0f%%, direction=%s",
                market_id[:10],
                price_change * 100,
                direction,
            )

            return PriceJump(
                signal_type="price_jump",
                market_id=market_id,
                timestamp=datetime.now(),
                confidence=confidence,
                details={"market_name": market_name},
                price_before=previous_price,
                price_after=current_price,
                price_change=price_change,
                direction=direction,
            )

        return None


class FreshWalletDetector:
    """
    Detects trades from fresh wallets.

    Adapted from polymarket-insider-tracker (MIT License).
    A wallet is considered fresh if:
    - Nonce <= max_nonce (default 5)
    - Age < max_age_hours (default 48 hours)
    """

    def __init__(
        self,
        min_trade_size: Decimal = DEFAULT_MIN_TRADE_SIZE,
        max_nonce: int = DEFAULT_MAX_NONCE,
        max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    ):
        self.min_trade_size = min_trade_size
        self.max_nonce = max_nonce
        self.max_age_hours = max_age_hours

    def is_wallet_fresh(self, profile: WalletProfile) -> bool:
        """
        Check if wallet meets freshness criteria.

        Args:
            profile: Wallet profile to check

        Returns:
            True if wallet is fresh
        """
        # Must have few transactions
        if profile.nonce > self.max_nonce:
            return False

        # If age is known, must be recent
        if profile.age_hours is not None and profile.age_hours > self.max_age_hours:
            return False

        return True

    def calculate_confidence(
        self,
        profile: WalletProfile,
        trade_size: Decimal,
    ) -> tuple[float, Dict[str, float]]:
        """
        Calculate confidence score based on multiple factors.

        Confidence scoring (from polymarket-insider-tracker):
        - Base: 0.5 (fresh wallet detected)
        - +0.2 if nonce == 0 (brand new wallet)
        - +0.1 if age < 2 hours (very young)
        - +0.1 if trade size > $10,000 (large trade)

        Returns:
            Tuple of (confidence_score, factors_dict)
        """
        factors: Dict[str, float] = {"base": BASE_CONFIDENCE}
        confidence = BASE_CONFIDENCE

        # Brand new wallet bonus
        if profile.nonce == 0:
            factors["brand_new"] = BRAND_NEW_BONUS
            confidence += BRAND_NEW_BONUS

        # Very young wallet bonus
        if profile.age_hours is not None and profile.age_hours < 2.0:
            factors["very_young"] = VERY_YOUNG_BONUS
            confidence += VERY_YOUNG_BONUS

        # Large trade bonus
        if trade_size > LARGE_TRADE_THRESHOLD:
            factors["large_trade"] = LARGE_TRADE_BONUS
            confidence += LARGE_TRADE_BONUS

        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))

        return confidence, factors

    def detect(
        self,
        profile: WalletProfile,
        trade_size: Decimal,
        market_id: str,
        market_name: str = "",
    ) -> Optional[FreshWalletSignal]:
        """
        Detect if a trade is from a fresh wallet.

        Args:
            profile: Wallet profile
            trade_size: Size of the trade in USD
            market_id: Market identifier
            market_name: Optional market name

        Returns:
            FreshWalletSignal if detected, None otherwise
        """
        # Filter by minimum trade size
        if trade_size < self.min_trade_size:
            return None

        # Check freshness
        if not self.is_wallet_fresh(profile):
            return None

        # Calculate confidence
        confidence, factors = self.calculate_confidence(profile, trade_size)

        logger.info(
            "Fresh wallet detected: wallet=%s, nonce=%d, age=%s, size=%s, confidence=%.2f",
            profile.address[:10] + "...",
            profile.nonce,
            f"{profile.age_hours:.1f}h" if profile.age_hours else "unknown",
            trade_size,
            confidence,
        )

        return FreshWalletSignal(
            signal_type="fresh_wallet",
            market_id=market_id,
            timestamp=datetime.now(),
            confidence=confidence,
            details={"market_name": market_name},
            wallet_address=profile.address,
            wallet_age_hours=profile.age_hours,
            wallet_nonce=profile.nonce,
            trade_size=trade_size,
            factors=factors,
        )


class AnomalyDetector:
    """
    Main anomaly detection engine combining all detectors.
    """

    def __init__(self):
        self.volume_detector = VolumeDetector()
        self.price_detector = PriceDetector()
        self.fresh_wallet_detector = FreshWalletDetector()

    def detect_all(
        self,
        market_id: str,
        market_name: str = "",
        current_volume: Optional[float] = None,
        current_price: Optional[float] = None,
        wallet_profile: Optional[WalletProfile] = None,
        trade_size: Optional[Decimal] = None,
    ) -> List[AnomalySignal]:
        """
        Run all detectors and return any signals.

        Args:
            market_id: Market identifier
            market_name: Market name/question
            current_volume: Current 24h volume
            current_price: Current price
            wallet_profile: Wallet profile for fresh wallet detection
            trade_size: Trade size for fresh wallet detection

        Returns:
            List of detected anomaly signals
        """
        signals = []

        if current_volume is not None:
            volume_signal = self.volume_detector.detect(
                market_id, current_volume, market_name
            )
            if volume_signal:
                signals.append(volume_signal)

        if current_price is not None:
            price_signal = self.price_detector.detect(
                market_id, current_price, market_name
            )
            if price_signal:
                signals.append(price_signal)

        if wallet_profile is not None and trade_size is not None:
            fresh_signal = self.fresh_wallet_detector.detect(
                wallet_profile, trade_size, market_id, market_name
            )
            if fresh_signal:
                signals.append(fresh_signal)

        return signals


if __name__ == "__main__":
    # Test the detectors
    print("Testing Anomaly Detectors...")

    detector = AnomalyDetector()

    # Test volume detector
    print("\n📊 Volume Detector:")
    for i, vol in enumerate([10000, 12000, 11000, 15000, 50000]):
        signal = detector.volume_detector.detect("test-market", vol, "Test Market")
        if signal:
            print(f"  Spike at observation {i}: {signal.spike_ratio:.1f}x, z={signal.z_score:.1f}")

    # Test fresh wallet detector
    print("\n👛 Fresh Wallet Detector:")
    fresh_profile = WalletProfile(
        address="0x" + "a" * 40,
        nonce=1,
        age_hours=1.5,
        is_fresh=True,
    )
    signal = detector.fresh_wallet_detector.detect(
        fresh_profile,
        Decimal("25000"),
        "test-market",
        "Test Market"
    )
    if signal:
        print(f"  Detected: confidence={signal.confidence:.2f}")
        print(f"  Factors: {signal.factors}")

    # Test with non-fresh wallet
    old_profile = WalletProfile(
        address="0x" + "b" * 40,
        nonce=50,
        age_hours=720,  # 30 days
        is_fresh=False,
    )
    signal = detector.fresh_wallet_detector.detect(
        old_profile,
        Decimal("25000"),
        "test-market",
        "Test Market"
    )
    print(f"  Old wallet detected: {signal is not None}")
