"""KicksDB marketplace adapter — aggregates StockX, GOAT, and 40+ shops via kicks.dev v3 API."""

import logging
import os

import requests

from src.marketplaces.base import MarketplaceAdapter
from src.models.sneaker import Condition, SneakerListing

logger = logging.getLogger(__name__)

# Platforms queried through KicksDB and the marketplace label used in results.
PLATFORMS = [
    {"path": "stockx", "label": "StockX"},
    {"path": "goat", "label": "GOAT"},
]


class KicksDBAdapter(MarketplaceAdapter):
    """
    Pulls data from KicksDB (kicks.dev) v3 API, which provides StockX and
    GOAT product data with size-level pricing via a single API key.

    50,000 free requests/month — sign up at https://kicks.dev/

    Requires:
        KICKSDB_API_KEY environment variable.
    """

    BASE_URL = "https://api.kicks.dev/v3"

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

    # ------------------------------------------------------------------
    # Raw API calls
    # ------------------------------------------------------------------

    def _search_platform(self, platform: str, query: str) -> list[dict]:
        """Search a single platform (stockx or goat) and return the product list."""
        resp = requests.get(
            f"{self.BASE_URL}/{platform}/products",
            headers=self._headers(),
            params={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []) if isinstance(data, dict) else data

    def _get_product_detail(self, platform: str, slug: str) -> dict | None:
        """Fetch a single product with variant-level pricing."""
        resp = requests.get(
            f"{self.BASE_URL}/{platform}/products/{slug}",
            headers=self._headers(),
            params={"display[variants]": "true"},
            timeout=15,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") if isinstance(data, dict) else None

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_stockx_product(
        product: dict, size: float | None = None
    ) -> list[SneakerListing]:
        """Parse a StockX product dict into SneakerListings."""
        title = product.get("title", "Unknown")
        sku = product.get("sku", "")
        image = product.get("image", "")
        link = product.get("link", "")
        min_price = product.get("min_price")
        max_price = product.get("max_price")

        listings: list[SneakerListing] = []

        # If we have variant-level data, use it
        variants = product.get("variants") or []
        for v in variants:
            lowest_ask = v.get("lowest_ask")
            if not lowest_ask:
                continue
            try:
                sz = float(v.get("size", 0))
                px = float(lowest_ask)
            except (ValueError, TypeError):
                continue
            if size and sz != size:
                continue
            listings.append(
                SneakerListing(
                    marketplace="StockX",
                    name=title,
                    style_code=sku,
                    size=sz,
                    ask_price=px,
                    condition=Condition.NEW,
                    url=link,
                    image_url=image,
                )
            )

        # Fallback: no variants but we have min_price from search results
        if not listings and min_price:
            try:
                px = float(min_price)
            except (ValueError, TypeError):
                return []
            listings.append(
                SneakerListing(
                    marketplace="StockX",
                    name=title,
                    style_code=sku,
                    size=size or 0.0,
                    ask_price=px,
                    condition=Condition.NEW,
                    url=link,
                    image_url=image,
                )
            )

        return listings

    @staticmethod
    def _parse_goat_product(
        product: dict, size: float | None = None
    ) -> list[SneakerListing]:
        """Parse a GOAT product dict into SneakerListings."""
        name = product.get("name", "Unknown")
        sku = product.get("sku", "")
        image = product.get("image_url", "")
        link = product.get("link", "")

        listings: list[SneakerListing] = []

        # Variant-level pricing
        variants = product.get("variants") or []
        for v in variants:
            lowest_ask = v.get("lowest_ask")
            if not lowest_ask:
                continue
            available = v.get("available", True)
            if not available:
                continue
            try:
                sz = float(v.get("size", 0))
                px = float(lowest_ask)
            except (ValueError, TypeError):
                continue
            if size and sz != size:
                continue
            listings.append(
                SneakerListing(
                    marketplace="GOAT",
                    name=name,
                    style_code=sku,
                    size=sz,
                    ask_price=px,
                    condition=Condition.NEW,
                    url=link,
                    image_url=image,
                )
            )

        return listings

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        all_listings: list[SneakerListing] = []

        for plat in PLATFORMS:
            try:
                products = self._search_platform(plat["path"], query)
            except Exception as e:
                logger.warning("KicksDB %s search failed: %s", plat["label"], e)
                continue

            for product in products[:10]:
                slug = product.get("slug", "")
                if not slug:
                    continue

                # Fetch full product with variant pricing
                try:
                    detail = self._get_product_detail(plat["path"], slug)
                except Exception as e:
                    logger.warning("KicksDB %s detail failed for %s: %s", plat["label"], slug, e)
                    detail = None

                source = detail if detail else product

                if plat["path"] == "stockx":
                    all_listings.extend(self._parse_stockx_product(source, size))
                else:
                    all_listings.extend(self._parse_goat_product(source, size))

        return all_listings

    def get_by_style_code(
        self, style_code: str, size: float | None = None
    ) -> list[SneakerListing]:
        all_listings: list[SneakerListing] = []

        for plat in PLATFORMS:
            try:
                products = self._search_platform(plat["path"], style_code)
            except Exception as e:
                logger.warning("KicksDB %s search failed: %s", plat["label"], e)
                continue

            for product in products:
                sku = product.get("sku", "")
                if sku.replace(" ", "").upper() != style_code.replace(" ", "").upper():
                    continue

                slug = product.get("slug", "")
                if not slug:
                    continue

                try:
                    detail = self._get_product_detail(plat["path"], slug)
                except Exception:
                    detail = None

                source = detail if detail else product

                if plat["path"] == "stockx":
                    all_listings.extend(self._parse_stockx_product(source, size))
                else:
                    all_listings.extend(self._parse_goat_product(source, size))

        return all_listings
