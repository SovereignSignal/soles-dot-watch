"""GOAT marketplace adapter using Retailed.io API."""

import os

import requests

from src.marketplaces.base import MarketplaceAdapter
from src.models.sneaker import Condition, SneakerListing


class GoatAdapter(MarketplaceAdapter):
    """
    Pulls sneaker data from GOAT via the Retailed.io API.

    Requires:
        RETAILED_API_KEY environment variable.
        Get 50 free requests at https://retailed.io/
    """

    SEARCH_URL = "https://api.retailed.io/v1/goat/search"
    PRICES_URL = "https://api.retailed.io/v1/goat/prices"

    def __init__(self):
        self._api_key = os.environ.get("RETAILED_API_KEY", "")

    @property
    def name(self) -> str:
        return "GOAT"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        if not self.configured:
            raise RuntimeError(
                "Retailed API key not set. Set RETAILED_API_KEY env var. "
                "Get 50 free requests at https://retailed.io/"
            )
        return {"x-api-key": self._api_key}

    def _search_raw(self, query: str) -> list[dict]:
        resp = requests.get(
            self.SEARCH_URL,
            headers=self._headers(),
            params={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("results", [])

    def _get_prices(self, product_id: str) -> dict:
        """Get size-level pricing for a GOAT product."""
        resp = requests.get(
            self.PRICES_URL,
            headers=self._headers(),
            params={"productId": product_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_product(
        self, product: dict, size: float | None = None
    ) -> list[SneakerListing]:
        name = product.get("name", "Unknown")
        style_code = product.get("sku", "")
        retail = product.get("retailPrice")
        image = product.get("image", "")
        slug = product.get("slug", "")
        url = f"https://www.goat.com/sneakers/{slug}" if slug else ""

        # Try to get size-level prices if available
        sizes = product.get("sizes", {})
        if not sizes:
            # Use the product-level lowest price
            lowest = product.get("lowestPrice") or product.get("lowest_price_cents")
            if lowest:
                px = float(lowest)
                # Some APIs return cents
                if px > 5000:
                    px = px / 100
                return [
                    SneakerListing(
                        marketplace=self.name,
                        name=name,
                        style_code=style_code,
                        size=size or 0.0,
                        ask_price=px,
                        condition=Condition.NEW,
                        retail_price=float(retail) if retail else None,
                        url=url,
                        image_url=image,
                    )
                ]
            return []

        listings = []
        for sz_str, price in sizes.items():
            try:
                sz = float(sz_str)
                px = float(price)
            except (ValueError, TypeError):
                continue

            if px > 5000:
                px = px / 100

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
                    retail_price=float(retail) if retail else None,
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
            sku = product.get("sku", "")
            if sku.upper() == style_code.upper():
                results.extend(self._parse_product(product, size))
        return results
