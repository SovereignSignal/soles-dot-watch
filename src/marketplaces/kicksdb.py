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

    @staticmethod
    def _norm_sku(sku: str) -> str:
        """Normalize SKU for cross-platform matching (strip non-alphanumeric)."""
        return "".join(c for c in sku if c.isalnum()).upper()

    def _fetch_and_parse(
        self, plat_path: str, slug: str, product: dict, size: float | None = None,
    ) -> list[SneakerListing]:
        """Fetch variant details for a product and parse into listings."""
        try:
            detail = self._get_product_detail(plat_path, slug)
        except Exception as e:
            logger.warning("KicksDB %s detail failed for %s: %s", plat_path, slug, e)
            detail = None
        source = detail if detail else product
        if plat_path == "stockx":
            return self._parse_stockx_product(source, size)
        return self._parse_goat_product(source, size)

    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        all_listings: list[SneakerListing] = []

        # ---- Step 1: Search StockX for the query ----
        try:
            stockx_products = self._search_platform("stockx", query)
        except Exception as e:
            logger.warning("KicksDB StockX search failed: %s", e)
            stockx_products = []

        # ---- Step 2: Fetch details for top StockX results ----
        stockx_skus_fetched: dict[str, str] = {}  # norm_sku -> product_name
        for product in stockx_products[:5]:
            slug = product.get("slug", "")
            sku = product.get("sku", "")
            if not slug:
                continue
            all_listings.extend(self._fetch_and_parse("stockx", slug, product, size))
            if sku:
                stockx_skus_fetched[self._norm_sku(sku)] = product.get("title", "")

        # ---- Step 3: For each StockX SKU, look it up on GOAT for cross-market data ----
        goat_skus_found: set[str] = set()
        for norm_sku, name in stockx_skus_fetched.items():
            # Search GOAT using the raw SKU (with original formatting)
            # Find the original SKU from the products list
            raw_sku = ""
            for p in stockx_products:
                if p.get("sku") and self._norm_sku(p["sku"]) == norm_sku:
                    raw_sku = p["sku"]
                    break
            search_term = raw_sku or name
            try:
                goat_results = self._search_platform("goat", search_term)
            except Exception as e:
                logger.warning("KicksDB GOAT lookup failed for %s: %s", search_term, e)
                continue

            # Find the matching product on GOAT by SKU
            for gp in goat_results:
                goat_sku = gp.get("sku", "")
                goat_slug = gp.get("slug", "")
                if goat_sku and goat_slug and self._norm_sku(goat_sku) == norm_sku:
                    goat_skus_found.add(norm_sku)
                    all_listings.extend(self._fetch_and_parse("goat", goat_slug, gp, size))
                    break

        # ---- Step 4: Also search GOAT directly for extra coverage ----
        try:
            goat_products = self._search_platform("goat", query)
        except Exception as e:
            logger.warning("KicksDB GOAT search failed: %s", e)
            goat_products = []

        for product in goat_products[:3]:
            slug = product.get("slug", "")
            sku = product.get("sku", "")
            if not slug:
                continue
            norm = self._norm_sku(sku) if sku else ""
            # Skip if we already fetched this SKU from GOAT
            if norm and norm in goat_skus_found:
                continue
            all_listings.extend(self._fetch_and_parse("goat", slug, product, size))
            # If this GOAT product wasn't in StockX results, try to find it there
            if norm and norm not in stockx_skus_fetched and sku:
                try:
                    sx_results = self._search_platform("stockx", sku)
                    for sp in sx_results:
                        sx_sku = sp.get("sku", "")
                        sx_slug = sp.get("slug", "")
                        if sx_sku and sx_slug and self._norm_sku(sx_sku) == norm:
                            all_listings.extend(self._fetch_and_parse("stockx", sx_slug, sp, size))
                            break
                except Exception:
                    pass

        logger.info(
            "KicksDB search: %d StockX products, %d GOAT cross-matches, %d total listings",
            len(stockx_skus_fetched), len(goat_skus_found), len(all_listings),
        )

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
