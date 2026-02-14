"""Tests for the core arbitrage detection engine."""

from src.arbitrage import DEFAULT_SELLER_FEES, find_arbitrage
from src.models.sneaker import ArbitrageOpportunity, Condition, SneakerListing


def _listing(marketplace: str, style_code: str, size: float, ask_price: float) -> SneakerListing:
    """Helper to create a minimal listing for testing."""
    return SneakerListing(
        marketplace=marketplace,
        name=f"Test Shoe {style_code}",
        style_code=style_code,
        size=size,
        ask_price=ask_price,
        condition=Condition.NEW,
    )


class TestFindArbitrage:
    def test_basic_opportunity(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 300.00),
            _listing("eBay", "ABC-123", 10.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 1
        opp = opps[0]
        assert opp.buy_marketplace == "eBay"
        assert opp.sell_marketplace == "StockX"
        assert opp.gross_spread == 50.00

    def test_no_opportunity_same_marketplace(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 300.00),
            _listing("StockX", "ABC-123", 10.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 0

    def test_no_opportunity_same_price(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 300.00),
            _listing("GOAT", "ABC-123", 10.0, 300.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 0

    def test_min_gross_spread_filter(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 260.00),
            _listing("eBay", "ABC-123", 10.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=15.0)
        assert len(opps) == 0

    def test_different_sizes_not_matched(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 300.00),
            _listing("eBay", "ABC-123", 11.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 0

    def test_different_style_codes_not_matched(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 300.00),
            _listing("eBay", "XYZ-789", 10.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 0

    def test_style_code_case_insensitive(self):
        listings = [
            _listing("StockX", "abc-123", 10.0, 300.00),
            _listing("eBay", "ABC-123", 10.0, 250.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        assert len(opps) == 1

    def test_multiple_marketplaces(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 500.00),
            _listing("GOAT", "ABC-123", 10.0, 400.00),
            _listing("eBay", "ABC-123", 10.0, 300.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0, min_net_profit=-999)
        # eBay->StockX, eBay->GOAT, GOAT->StockX = 3 pairs
        assert len(opps) == 3
        # Best opportunity first (highest net profit)
        assert opps[0].buy_marketplace == "eBay"
        assert opps[0].sell_marketplace == "StockX"

    def test_sorted_by_net_profit_descending(self):
        listings = [
            _listing("StockX", "ABC-123", 10.0, 340.00),
            _listing("GOAT", "ABC-123", 10.0, 325.00),
            _listing("eBay", "ABC-123", 10.0, 300.00),
        ]
        opps = find_arbitrage(listings, min_gross_spread=0.0)
        nets = [o.net_profit(sell_fee_pct=DEFAULT_SELLER_FEES.get(o.sell_marketplace, 10.0)) for o in opps]
        assert nets == sorted(nets, reverse=True)

    def test_empty_listings(self):
        assert find_arbitrage([]) == []

    def test_single_listing(self):
        listings = [_listing("StockX", "ABC-123", 10.0, 300.00)]
        assert find_arbitrage(listings) == []


class TestArbitrageOpportunity:
    def test_gross_spread(self):
        buy = _listing("eBay", "ABC-123", 10.0, 250.00)
        sell = _listing("StockX", "ABC-123", 10.0, 300.00)
        opp = ArbitrageOpportunity(buy_listing=buy, sell_listing=sell, style_code="ABC-123", size=10.0)
        assert opp.gross_spread == 50.00

    def test_gross_spread_pct(self):
        buy = _listing("eBay", "ABC-123", 10.0, 200.00)
        sell = _listing("StockX", "ABC-123", 10.0, 250.00)
        opp = ArbitrageOpportunity(buy_listing=buy, sell_listing=sell, style_code="ABC-123", size=10.0)
        assert opp.gross_spread_pct == 25.0

    def test_net_profit(self):
        buy = _listing("eBay", "ABC-123", 10.0, 200.00)
        sell = _listing("StockX", "ABC-123", 10.0, 300.00)
        opp = ArbitrageOpportunity(buy_listing=buy, sell_listing=sell, style_code="ABC-123", size=10.0)
        # sell_net = 300 * (1 - 0.095) = 271.50, net = 271.50 - 200 = 71.50
        assert opp.net_profit(sell_fee_pct=9.5) == 71.50

    def test_net_profit_zero_buy_price(self):
        buy = _listing("eBay", "ABC-123", 10.0, 0.00)
        sell = _listing("StockX", "ABC-123", 10.0, 300.00)
        opp = ArbitrageOpportunity(buy_listing=buy, sell_listing=sell, style_code="ABC-123", size=10.0)
        assert opp.gross_spread_pct == 0.0

    def test_summary(self):
        buy = _listing("eBay", "ABC-123", 10.0, 250.00)
        sell = _listing("StockX", "ABC-123", 10.0, 300.00)
        opp = ArbitrageOpportunity(buy_listing=buy, sell_listing=sell, style_code="ABC-123", size=10.0)
        s = opp.summary()
        assert "eBay" in s
        assert "StockX" in s
        assert "$250.00" in s
        assert "$300.00" in s
