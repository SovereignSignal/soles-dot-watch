"""KicksDB marketplace adapter — aggregates 40+ sneaker shops."""

import os

import requests

from src.marketplaces.base import MarketplaceAdapter
from src.models.sneaker import Condition, SneakerListing


class KicksDBAdapter(MarketplaceAdapter):
    """
    Pulls data from KicksDB (kicks.dev), which aggregates pricing
    from StockX, GOAT, Flight Club, Kicks Crew, and 40+ other shops.

    This is the most powerful single source — 50,000 free requests/month.

    Requires:
        KICKSDB_API_KEY environment variable.
        Sign up at https://kicks.dev/
    """

    BASE_URL = "https://api.kicks.dev/v1"

    def __init__(self):
        self._api_key = os.environ.get("KICKSDB_API_KEY", "")

    @property
    def name(self) -> str:
        return "KicksDB"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        if not self.configured:
            raise RuntimeError(
                "KicksDB API key not set. Set KICKSDB_API_KEY env var. "
                "Get 50,000 free requests/month at https://kicks.dev/"
            )
        return {"Authorization": f"Bearer {self._api_key}"}

    def _search_raw(self, query: str, limit: int = 20) -> list[dict]:
        resp = requests.get(
            f"{self.BASE_URL}/search",
            headers=self._headers(),
            params={"query": query, "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("results", [])

    def _get_product(self, product_id: str) -> dict:
        """Get detailed product info including multi-marketplace pricing."""
        resp = requests.get(
            f"{self.BASE_URL}/products/{product_id}",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_product(
        self, product: dict, size: float | None = None
    ) -> list[SneakerListing]:
        """
        Parse a KicksDB product into multiple SneakerListings —
        one per marketplace×size combination.
        """
        name = product.get("name", "Unknown")
        style_code = product.get("sku") or product.get("styleId", "")
        retail = product.get("retailPrice")
        image = product.get("image", "")

        listings = []

        # KicksDB returns prices grouped by marketplace
        offers = product.get("offers", [])
        for offer in offers:
            marketplace = offer.get("merchant") or offer.get("source", "unknown")
            url = offer.get("url", "")

            # Offers may have size-level pricing or a single price
            size_prices = offer.get("sizes", {})
            if size_prices:
                for sz_str, px_val in size_prices.items():
                    try:
                        sz = float(sz_str)
                        px = float(px_val)
                    except (ValueError, TypeError):
                        continue
                    if size and sz != size:
                        continue
                    listings.append(
                        SneakerListing(
                            marketplace=marketplace,
                            name=name,
                            style_code=style_code,
                            size=sz,
                            ask_price=px,
                            condition=Condition.NEW,
                            retail_price=float(retail) if retail else None,
                            url=url,
                            image_url=image,
                        )
                    )
            else:
                # Single price for this marketplace
                px_val = offer.get("price") or offer.get("lowest_price")
                if px_val:
                    try:
                        px = float(px_val)
                    except (ValueError, TypeError):
                        continue
                    listings.append(
                        SneakerListing(
                            marketplace=marketplace,
                            name=name,
                            style_code=style_code,
                            size=size or 0.0,
                            ask_price=px,
                            condition=Condition.NEW,
                            retail_price=float(retail) if retail else None,
                            url=url,
                            image_url=image,
                        )
                    )

        return listings

    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        q = query
        raw = self._search_raw(q)
        all_listings = []
        for product in raw:
            all_listings.extend(self._parse_product(product, size))
        return all_listings

    def get_by_style_code(
        self, style_code: str, size: float | None = None
    ) -> list[SneakerListing]:
        raw = self._search_raw(style_code)
        results = []
        for product in raw:
            sku = product.get("sku") or product.get("styleId", "")
            if sku.upper() == style_code.upper():
                results.extend(self._parse_product(product, size))
        return results
