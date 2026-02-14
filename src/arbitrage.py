"""Core arbitrage detection engine."""

from collections import defaultdict

from src.models.sneaker import ArbitrageOpportunity, SneakerListing


# Default seller fee percentages by marketplace
DEFAULT_SELLER_FEES = {
    "StockX": 9.5,
    "stockx": 9.5,
    "GOAT": 9.5,
    "goat": 9.5,
    "Flight Club": 9.5,
    "flightclub": 9.5,
    "eBay": 13.25,
    "ebay": 13.25,
    "Grailed": 9.0,
    "grailed": 9.0,
    "Kicks Crew": 8.0,
    "kickscrew": 8.0,
}


def find_arbitrage(
    listings: list[SneakerListing],
    min_gross_spread: float = 10.0,
    min_net_profit: float = 0.0,
    seller_fees: dict[str, float] | None = None,
) -> list[ArbitrageOpportunity]:
    """
    Find arbitrage opportunities across marketplace listings.

    Groups listings by (style_code, size), then for each group finds
    pairs where one marketplace is cheaper than another.

    Args:
        listings: All listings gathered from various marketplaces.
        min_gross_spread: Minimum dollar spread to qualify (default $10).
        min_net_profit: Minimum estimated net profit after fees (default $0).
        seller_fees: Override seller fee percentages by marketplace name.

    Returns:
        List of ArbitrageOpportunity, sorted by net profit descending.
    """
    fees = DEFAULT_SELLER_FEES.copy()
    if seller_fees:
        fees.update(seller_fees)

    # Group by (normalized_style_code, size)
    # Normalize SKUs so "DZ5485-100" (StockX) matches "DZ5485 100" (GOAT)
    groups: dict[tuple[str, float], list[SneakerListing]] = defaultdict(list)
    for listing in listings:
        if listing.style_code and listing.size > 0:
            norm = "".join(c for c in listing.style_code if c.isalnum()).upper()
            key = (norm, listing.size)
            groups[key].append(listing)

    opportunities = []

    for (_style, _size), group in groups.items():
        if len(group) < 2:
            continue

        # Deduplicate: keep cheapest listing per marketplace
        best_by_market: dict[str, SneakerListing] = {}
        for listing in group:
            mk = listing.marketplace.lower()
            if mk not in best_by_market or listing.ask_price < best_by_market[mk].ask_price:
                best_by_market[mk] = listing

        market_listings = list(best_by_market.values())

        # Compare all pairs
        for buy in market_listings:
            for sell in market_listings:
                if buy.marketplace.lower() == sell.marketplace.lower():
                    continue
                if sell.ask_price <= buy.ask_price:
                    continue

                opp = ArbitrageOpportunity(
                    buy_listing=buy,
                    sell_listing=sell,
                    style_code=buy.style_code,
                    size=buy.size,
                )

                if opp.gross_spread < min_gross_spread:
                    continue

                sell_fee = fees.get(sell.marketplace, fees.get(sell.marketplace.lower(), 10.0))
                net = opp.net_profit(sell_fee_pct=sell_fee)
                if net < min_net_profit:
                    continue

                opportunities.append(opp)

    # Sort by net profit, best first
    opportunities.sort(
        key=lambda o: o.net_profit(
            sell_fee_pct=fees.get(
                o.sell_marketplace, fees.get(o.sell_marketplace.lower(), 10.0)
            )
        ),
        reverse=True,
    )

    return opportunities
