"""eBay marketplace adapter using the official Browse API."""

import os
import base64
from datetime import datetime, timedelta

import requests

from src.marketplaces.base import MarketplaceAdapter
from src.models.sneaker import Condition, SneakerListing


class EbayAdapter(MarketplaceAdapter):
    """
    Pulls sneaker listings from eBay's Browse API.

    Requires:
        EBAY_CLIENT_ID and EBAY_CLIENT_SECRET environment variables.
        Get these free at https://developer.ebay.com/
    """

    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    # eBay category IDs for men's athletic shoes
    SNEAKER_CATEGORY = "15709"

    def __init__(self):
        self._client_id = os.environ.get("EBAY_CLIENT_ID", "")
        self._client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")
        self._token: str | None = None
        self._token_expiry: datetime | None = None

    @property
    def name(self) -> str:
        return "eBay"

    @property
    def configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def _get_token(self) -> str:
        """Get an OAuth application token (Client Credentials Grant)."""
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        if not self.configured:
            raise RuntimeError(
                "eBay API credentials not set. "
                "Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET env vars. "
                "Register at https://developer.ebay.com/"
            )

        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        resp = requests.post(
            self.TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = datetime.now() + timedelta(
            seconds=data.get("expires_in", 7200) - 60
        )
        return self._token

    def _search_raw(self, query: str, limit: int = 50) -> list[dict]:
        token = self._get_token()
        params = {
            "q": query,
            "category_ids": self.SNEAKER_CATEGORY,
            "filter": "conditionIds:{1000}",  # New with tags
            "sort": "price",
            "limit": str(limit),
        }
        resp = requests.get(
            self.SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("itemSummaries", [])

    def _parse_listing(self, item: dict, style_code: str = "") -> SneakerListing | None:
        """Convert an eBay item summary to a SneakerListing."""
        price_info = item.get("price", {})
        price_val = price_info.get("value")
        if not price_val:
            return None

        try:
            price = float(price_val)
        except (ValueError, TypeError):
            return None

        title = item.get("title", "")

        # Try to extract size from title — common pattern: "Size 10" or "Sz 10.5"
        size = self._extract_size(title)

        condition = Condition.NEW
        cond_str = item.get("condition", "")
        if "used" in str(cond_str).lower():
            condition = Condition.USED

        return SneakerListing(
            marketplace=self.name,
            name=title,
            style_code=style_code,
            size=size,
            ask_price=price,
            condition=condition,
            url=item.get("itemWebUrl", ""),
            image_url=item.get("image", {}).get("imageUrl", ""),
        )

    @staticmethod
    def _extract_size(title: str) -> float:
        """Best-effort extraction of shoe size from a listing title."""
        import re

        patterns = [
            r"[Ss]i?ze?\s*(\d{1,2}(?:\.\d)?)",
            r"[Ss]z\.?\s*(\d{1,2}(?:\.\d)?)",
            r"\b(\d{1,2}(?:\.\d)?)\s*US\b",
        ]
        for pat in patterns:
            m = re.search(pat, title)
            if m:
                return float(m.group(1))
        return 0.0

    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        q = f"Air Jordan {query}"
        if size:
            q += f" Size {size}"

        raw = self._search_raw(q)
        results = []
        for item in raw:
            listing = self._parse_listing(item)
            if listing:
                if size and listing.size and listing.size != size:
                    continue
                results.append(listing)
        return results

    def get_by_style_code(
        self, style_code: str, size: float | None = None
    ) -> list[SneakerListing]:
        q = style_code
        if size:
            q += f" Size {size}"

        raw = self._search_raw(q)
        results = []
        for item in raw:
            listing = self._parse_listing(item, style_code=style_code)
            if listing:
                listing.style_code = style_code
                if size and listing.size and listing.size != size:
                    continue
                results.append(listing)
        return results
