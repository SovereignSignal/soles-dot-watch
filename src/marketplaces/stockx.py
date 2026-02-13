"""StockX marketplace adapter using the RapidAPI Sneaker Database."""

import os

import requests

from src.marketplaces.base import MarketplaceAdapter
from src.models.sneaker import Condition, SneakerListing


class StockXAdapter(MarketplaceAdapter):
    """
    Pulls sneaker data via the Sneaker Database (StockX) on RapidAPI.

    This gives us StockX pricing without needing a direct StockX developer account.

    Requires:
        RAPIDAPI_KEY environment variable.
        Subscribe (free tier: 100 req/month) at:
        https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/sneaker-database-stockx
    """

    BASE_URL = "https://sneaker-database-stockx.p.rapidapi.com"

    def __init__(self):
        self._api_key = os.environ.get("RAPIDAPI_KEY", "")

    @property
    def name(self) -> str:
        return "StockX"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        if not self.configured:
            raise RuntimeError(
                "RapidAPI key not set. Set RAPIDAPI_KEY env var. "
                "Get a free key at https://rapidapi.com/"
            )
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": "sneaker-database-stockx.p.rapidapi.com",
        }

    def _search_raw(self, query: str, limit: int = 20) -> list[dict]:
        resp = requests.get(
            f"{self.BASE_URL}/getproducts",
            headers=self._headers(),
            params={"keywords": query, "limit": str(limit)},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json() if isinstance(resp.json(), list) else resp.json().get("products", [])

    def _parse_product(
        self, product: dict, size: float | None = None
    ) -> list[SneakerListing]:
        """Convert a product dict into listings (one per available size)."""
        name = product.get("shoeName") or product.get("title", "Unknown")
        style_code = product.get("styleID") or product.get("style_id", "")
        retail_str = product.get("retailPrice") or product.get("retail_price")
        retail = float(retail_str) if retail_str else None
        image = product.get("thumbnail") or product.get("image", "")
        url = product.get("resellLinks", {}).get("stockX", "")

        # Price map: size -> price from various resellers
        price_map = product.get("resellPrices", {}).get("stockX", {})
        if not price_map:
            # Fallback: try lowestResellPrice
            lowest = product.get("lowestResellPrice", {}).get("stockX")
            if lowest:
                price_map = {"0": float(lowest)}  # unknown size

        listings = []
        for sz_str, price in price_map.items():
            try:
                sz = float(sz_str)
                px = float(price)
            except (ValueError, TypeError):
                continue

            if size and sz != size:
                continue

            listings.append(
                SneakerListing(
                    marketplace=self.name,
                    name=name,
                    style_code=style_code,
                    size=sz,
                    ask_price=px,
                    condition=Condition.NEW,
                    retail_price=retail,
                    url=url,
                    image_url=image,
                )
            )
        return listings

    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        q = f"Air Jordan {query}"
        raw = self._search_raw(q)
        results = []
        for product in raw:
            results.extend(self._parse_product(product, size))
        return results

    def get_by_style_code(
        self, style_code: str, size: float | None = None
    ) -> list[SneakerListing]:
        raw = self._search_raw(style_code)
        results = []
        for product in raw:
            pid = product.get("styleID") or product.get("style_id", "")
            if pid.upper() == style_code.upper():
                results.extend(self._parse_product(product, size))
        return results
