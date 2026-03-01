"""
Wallet Profiler with Funding Chain Tracing
Adapted from polymarket-insider-tracker (MIT License)

Provides:
- Wallet history aggregation
- Win rate calculation
- Funding chain analysis (where did initial funds come from?)
- Trade pattern analysis
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from collections import defaultdict

logger = logging.getLogger(__name__)

# Funding source classifications (from polymarket-insider-tracker)
class FundingSource:
    """Known funding source classifications."""
    CEX = "cex"  # Centralized exchange (Coinbase, Binance, etc.)
    DEX = "dex"  # Decentralized exchange
    BRIDGE = "bridge"  # Cross-chain bridge
    MIXER = "mixer"  # Tornado Cash, etc. (HIGH RISK)
    CONTRACT = "contract"  # Smart contract
    DIRECT = "direct"  # Direct from another wallet
    UNKNOWN = "unknown"


# Known exchange/bridge addresses (subset - from polymarket-insider-tracker)
KNOWN_ADDRESSES = {
    # Centralized Exchanges
    "0x28c6c06298d514db089934071355e5743bf21d60": ("binance", FundingSource.CEX),
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": ("binance", FundingSource.CEX),
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": ("binance", FundingSource.CEX),
    "0x503828976d22510aad0201ac7ec88293211d23da": ("coinbase", FundingSource.CEX),
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": ("coinbase", FundingSource.CEX),
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": ("ftx", FundingSource.CEX),
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": ("kraken", FundingSource.CEX),
    # Bridges
    "0x8eb8a3b98659cce290402893d0123abb75e3ab28": ("polygon_bridge", FundingSource.BRIDGE),
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": ("polygon_bridge", FundingSource.BRIDGE),
    # Mixers (high risk)
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": ("tornado_cash", FundingSource.MIXER),
}


@dataclass
class FundingChain:
    """Represents the funding path for a wallet."""
    hops: List[Dict[str, Any]] = field(default_factory=list)
    original_source: Optional[str] = None
    source_type: str = FundingSource.UNKNOWN
    source_name: Optional[str] = None
    total_funded: Decimal = Decimal("0")
    risk_score: float = 0.0


@dataclass
class TradeRecord:
    """Individual trade record."""
    market_id: str
    timestamp: datetime
    side: str  # "buy" or "sell"
    outcome: str  # "yes" or "no"
    size: Decimal
    price: Decimal
    resolved_payout: Optional[Decimal] = None  # None if not yet resolved


@dataclass
class WalletProfile:
    """Comprehensive wallet profile."""
    address: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    nonce: int = 0
    age_hours: Optional[float] = None

    # Trade statistics
    total_trades: int = 0
    total_volume: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")
    win_count: int = 0
    loss_count: int = 0

    # Derived metrics
    win_rate: Optional[float] = None
    avg_trade_size: Optional[Decimal] = None
    roi: Optional[float] = None

    # Market preferences
    markets_traded: List[str] = field(default_factory=list)
    preferred_categories: List[str] = field(default_factory=list)

    # Cluster membership (from DBSCAN)
    cluster_id: Optional[int] = None
    is_sniper: bool = False

    # Funding chain
    funding_chain: Optional[FundingChain] = None

    # Risk flags
    risk_flags: List[str] = field(default_factory=list)
    risk_score: float = 0.0


class WalletProfiler:
    """
    Builds comprehensive wallet profiles from trade history.

    Adapted from polymarket-insider-tracker (MIT License).
    """

    def __init__(self):
        self._profiles: Dict[str, WalletProfile] = {}
        self._trades: Dict[str, List[TradeRecord]] = defaultdict(list)

    def record_trade(
        self,
        wallet_address: str,
        market_id: str,
        side: str,
        outcome: str,
        size: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
    ):
        """
        Record a trade for a wallet.

        Args:
            wallet_address: Wallet address
            market_id: Market identifier
            side: "buy" or "sell"
            outcome: "yes" or "no"
            size: Trade size in USD
            price: Trade price (0-1)
            timestamp: Trade timestamp
        """
        trade = TradeRecord(
            market_id=market_id,
            timestamp=self._to_utc(timestamp) or datetime.now(timezone.utc),
            side=side,
            outcome=outcome,
            size=size,
            price=price,
        )
        self._trades[wallet_address].append(trade)

        # Update profile
        self._update_profile(wallet_address, trade)

    def _update_profile(self, wallet_address: str, trade: TradeRecord):
        """Update wallet profile with new trade."""
        if wallet_address not in self._profiles:
            self._profiles[wallet_address] = WalletProfile(
                address=wallet_address,
                first_seen=trade.timestamp,
            )

        profile = self._profiles[wallet_address]
        profile.total_trades += 1
        profile.nonce = max(profile.nonce, profile.total_trades)
        profile.total_volume += trade.size
        profile.last_seen = trade.timestamp

        if trade.market_id not in profile.markets_traded:
            profile.markets_traded.append(trade.market_id)

        # Update age
        if profile.first_seen:
            first_seen_utc = self._to_utc(profile.first_seen) or profile.first_seen
            now_utc = datetime.now(timezone.utc)
            age_delta = now_utc - first_seen_utc
            profile.age_hours = age_delta.total_seconds() / 3600

        # Recalculate average trade size
        profile.avg_trade_size = profile.total_volume / Decimal(profile.total_trades)

    def record_resolution(
        self,
        wallet_address: str,
        market_id: str,
        payout: Decimal,
        cost_basis: Decimal,
    ):
        """
        Record market resolution for PnL tracking.

        Args:
            wallet_address: Wallet address
            market_id: Market identifier
            payout: Amount received
            cost_basis: Original investment
        """
        if wallet_address not in self._profiles:
            return

        profile = self._profiles[wallet_address]
        pnl = payout - cost_basis
        profile.total_pnl += pnl

        if pnl > 0:
            profile.win_count += 1
        else:
            profile.loss_count += 1

        # Update win rate
        total_resolved = profile.win_count + profile.loss_count
        if total_resolved > 0:
            profile.win_rate = profile.win_count / total_resolved

        # Update ROI
        if profile.total_volume > 0:
            profile.roi = float(profile.total_pnl / profile.total_volume)

    def get_profile(self, wallet_address: str) -> Optional[WalletProfile]:
        """Get wallet profile."""
        return self._profiles.get(wallet_address)

    def get_or_create_profile(
        self,
        wallet_address: str,
        nonce: int = 0,
        first_seen: Optional[datetime] = None,
    ) -> WalletProfile:
        """Get existing profile or create a new one."""
        if wallet_address not in self._profiles:
            self._profiles[wallet_address] = WalletProfile(
                address=wallet_address,
                nonce=nonce,
                first_seen=self._to_utc(first_seen) or datetime.now(timezone.utc),
            )
        return self._profiles[wallet_address]

    def analyze_funding_chain(
        self,
        wallet_address: str,
        funding_txs: List[Dict[str, Any]],
    ) -> FundingChain:
        """
        Analyze the funding chain for a wallet.

        This traces back where the wallet's funds originated from,
        flagging high-risk sources like mixers.

        Args:
            wallet_address: Wallet to analyze
            funding_txs: List of funding transactions (from Etherscan/similar)

        Returns:
            FundingChain object with source analysis
        """
        chain = FundingChain()
        total_funded = Decimal("0")
        largest_known_source_value = Decimal("0")

        for tx in funding_txs:
            from_addr = tx.get("from", "").lower()
            value = Decimal(str(tx.get("value", 0)))
            total_funded += value

            hop = {
                "from": from_addr,
                "value": value,
                "tx_hash": tx.get("hash", ""),
            }

            # Check if from a known source
            if from_addr in KNOWN_ADDRESSES:
                name, source_type = KNOWN_ADDRESSES[from_addr]
                hop["source_name"] = name
                hop["source_type"] = source_type

                # Track the largest funding source
                if value > largest_known_source_value:
                    chain.original_source = from_addr
                    chain.source_type = source_type
                    chain.source_name = name
                    largest_known_source_value = value

            chain.hops.append(hop)

        chain.total_funded = total_funded

        # Calculate risk score based on funding source
        if chain.source_type == FundingSource.MIXER:
            chain.risk_score = 0.9  # Very high risk
        elif chain.source_type == FundingSource.UNKNOWN:
            chain.risk_score = 0.5  # Medium risk
        elif chain.source_type == FundingSource.CEX:
            chain.risk_score = 0.2  # Lower risk (KYC'd source)
        else:
            chain.risk_score = 0.3

        # Store in profile
        if wallet_address in self._profiles:
            self._profiles[wallet_address].funding_chain = chain
            self._profiles[wallet_address].risk_score = max(
                self._profiles[wallet_address].risk_score,
                chain.risk_score
            )

            if chain.source_type == FundingSource.MIXER:
                self._profiles[wallet_address].risk_flags.append("mixer_funded")

        return chain

    def calculate_risk_flags(self, wallet_address: str) -> List[str]:
        """
        Calculate risk flags for a wallet.

        Returns list of risk indicators.
        """
        profile = self._profiles.get(wallet_address)
        if not profile:
            return []

        flags = []

        # Fresh wallet flag
        if profile.nonce <= 5 and (profile.age_hours or 0) < 48:
            flags.append("fresh_wallet")

        # Very new (sniper-like)
        if (profile.age_hours or 0) < 2:
            flags.append("very_new_wallet")

        # High win rate (suspiciously good)
        if profile.win_rate and profile.win_rate > 0.85 and profile.total_trades >= 5:
            flags.append("high_win_rate")

        # Large single trade
        if profile.avg_trade_size and profile.avg_trade_size > Decimal("50000"):
            flags.append("large_trader")

        # Funding chain flags
        if profile.funding_chain:
            if profile.funding_chain.source_type == FundingSource.MIXER:
                if "mixer_funded" not in flags:
                    flags.append("mixer_funded")
            elif profile.funding_chain.source_type == FundingSource.UNKNOWN:
                flags.append("unknown_funding")

        profile.risk_flags = flags
        return flags

    def get_all_profiles(self) -> List[WalletProfile]:
        """Get all tracked wallet profiles."""
        return list(self._profiles.values())

    def get_high_risk_wallets(self, min_risk_score: float = 0.5) -> List[WalletProfile]:
        """Get wallets exceeding risk threshold."""
        return [
            p for p in self._profiles.values()
            if p.risk_score >= min_risk_score
        ]

    @staticmethod
    def _to_utc(value: Optional[datetime]) -> Optional[datetime]:
        """Normalize datetimes to timezone-aware UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


if __name__ == "__main__":
    from decimal import Decimal

    print("Testing Wallet Profiler...")

    profiler = WalletProfiler()

    # Simulate some trades
    test_wallet = "0x" + "a" * 40

    print("\n📊 Recording trades...")
    for i in range(5):
        profiler.record_trade(
            wallet_address=test_wallet,
            market_id=f"market-{i % 2}",
            side="buy",
            outcome="yes",
            size=Decimal("5000"),
            price=Decimal("0.60"),
        )

    # Record some resolutions
    profiler.record_resolution(
        wallet_address=test_wallet,
        market_id="market-0",
        payout=Decimal("10000"),
        cost_basis=Decimal("3000"),
    )
    profiler.record_resolution(
        wallet_address=test_wallet,
        market_id="market-1",
        payout=Decimal("0"),
        cost_basis=Decimal("3000"),
    )

    # Get profile
    profile = profiler.get_profile(test_wallet)
    print(f"\n👛 Wallet Profile:")
    print(f"  Address: {profile.address[:10]}...")
    print(f"  Total trades: {profile.total_trades}")
    print(f"  Total volume: ${profile.total_volume}")
    print(f"  Win rate: {profile.win_rate:.1%}" if profile.win_rate else "  Win rate: N/A")
    print(f"  PnL: ${profile.total_pnl}")
    print(f"  Markets: {profile.markets_traded}")

    # Test funding chain analysis
    print("\n🔗 Testing funding chain...")
    mock_funding = [
        {"from": "0x722122df12d4e14e13ac3b6895a86e84145b6967", "value": 10.0, "hash": "0x123"},  # Tornado Cash
    ]
    chain = profiler.analyze_funding_chain(test_wallet, mock_funding)
    print(f"  Source type: {chain.source_type}")
    print(f"  Source name: {chain.source_name}")
    print(f"  Risk score: {chain.risk_score}")

    # Calculate risk flags
    flags = profiler.calculate_risk_flags(test_wallet)
    print(f"\n⚠️ Risk flags: {flags}")
