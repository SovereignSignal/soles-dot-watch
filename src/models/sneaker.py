"""Data models for sneaker listings and arbitrage opportunities."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Condition(Enum):
    NEW = "new"
    USED = "used"
    UNKNOWN = "unknown"


@dataclass
class SneakerListing:
    """A single listing for a sneaker on a marketplace."""

    marketplace: str
    name: str
    style_code: str  # e.g. "DZ5485-612" — the unique Nike style ID
    size: float
    ask_price: float  # lowest price someone is selling for (USD)
    condition: Condition = Condition.NEW
    url: str = ""
    bid_price: float | None = None  # highest price someone is offering to buy
    last_sale_price: float | None = None
    retail_price: float | None = None
    image_url: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def display_name(self) -> str:
        return f"{self.name} (Size {self.size})"


@dataclass
class ArbitrageOpportunity:
    """An opportunity to buy on one marketplace and sell on another."""

    buy_listing: SneakerListing
    sell_listing: SneakerListing
    style_code: str
    size: float

    @property
    def gross_spread(self) -> float:
        """Raw price difference before fees."""
        return self.sell_listing.ask_price - self.buy_listing.ask_price

    @property
    def gross_spread_pct(self) -> float:
        """Gross spread as a percentage of the buy price."""
        if self.buy_listing.ask_price == 0:
            return 0.0
        return (self.gross_spread / self.buy_listing.ask_price) * 100

    def net_profit(self, sell_fee_pct: float = 9.5, buy_tax_pct: float = 0.0) -> float:
        """
        Estimated net profit after marketplace fees.

        Args:
            sell_fee_pct: Seller fee percentage on the sell platform (default 9.5% for StockX).
            buy_tax_pct: Sales tax percentage on the buy (default 0%).
        """
        buy_total = self.buy_listing.ask_price * (1 + buy_tax_pct / 100)
        sell_net = self.sell_listing.ask_price * (1 - sell_fee_pct / 100)
        return sell_net - buy_total

    @property
    def buy_marketplace(self) -> str:
        return self.buy_listing.marketplace

    @property
    def sell_marketplace(self) -> str:
        return self.sell_listing.marketplace

    def summary(self) -> str:
        return (
            f"Buy on {self.buy_marketplace} @ ${self.buy_listing.ask_price:.2f} → "
            f"Sell on {self.sell_marketplace} @ ${self.sell_listing.ask_price:.2f} | "
            f"Gross: ${self.gross_spread:.2f} ({self.gross_spread_pct:.1f}%) | "
            f"Est. Net: ${self.net_profit():.2f}"
        )
