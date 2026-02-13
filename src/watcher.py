"""High-level watcher that coordinates marketplace queries and arbitrage detection."""

from src.arbitrage import find_arbitrage
from src.marketplaces.base import MarketplaceAdapter
from src.marketplaces.ebay import EbayAdapter
from src.marketplaces.goat import GoatAdapter
from src.marketplaces.kicksdb import KicksDBAdapter
from src.marketplaces.stockx import StockXAdapter
from src.models.sneaker import ArbitrageOpportunity, SneakerListing


def get_available_adapters() -> list[MarketplaceAdapter]:
    """Return all marketplace adapters that have credentials configured."""
    all_adapters = [
        KicksDBAdapter(),
        StockXAdapter(),
        GoatAdapter(),
        EbayAdapter(),
    ]
    return [a for a in all_adapters if a.configured]


def scan_for_arbitrage(
    query: str,
    size: float | None = None,
    style_code: str | None = None,
    min_profit: float = 0.0,
    adapters: list[MarketplaceAdapter] | None = None,
) -> tuple[list[SneakerListing], list[ArbitrageOpportunity]]:
    """
    Scan configured marketplaces for a sneaker and find arbitrage opportunities.

    Args:
        query: Search term (e.g. "Air Jordan 1 Retro High OG Chicago").
        size: Optional shoe size to filter.
        style_code: Optional style code for exact match.
        min_profit: Minimum net profit to include.
        adapters: Override which adapters to use.

    Returns:
        Tuple of (all_listings, opportunities).
    """
    if adapters is None:
        adapters = get_available_adapters()

    if not adapters:
        raise RuntimeError(
            "No marketplace APIs configured! Set at least one of:\n"
            "  KICKSDB_API_KEY  — https://kicks.dev/ (recommended, 50K free/month)\n"
            "  RAPIDAPI_KEY     — https://rapidapi.com/ (StockX data, 100 free/month)\n"
            "  RETAILED_API_KEY — https://retailed.io/ (GOAT data, 50 free)\n"
            "  EBAY_CLIENT_ID + EBAY_CLIENT_SECRET — https://developer.ebay.com/"
        )

    all_listings: list[SneakerListing] = []
    errors: list[str] = []

    for adapter in adapters:
        try:
            if style_code:
                results = adapter.get_by_style_code(style_code, size)
            else:
                results = adapter.search(query, size)
            all_listings.extend(results)
        except Exception as e:
            errors.append(f"{adapter.name}: {e}")

    if errors:
        import sys
        for err in errors:
            print(f"  Warning: {err}", file=sys.stderr)

    opportunities = find_arbitrage(all_listings, min_net_profit=min_profit)

    return all_listings, opportunities
