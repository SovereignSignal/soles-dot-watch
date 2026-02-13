"""Base class for marketplace adapters."""

from abc import ABC, abstractmethod

from src.models.sneaker import SneakerListing


class MarketplaceAdapter(ABC):
    """Abstract base for all marketplace data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable marketplace name."""
        ...

    @abstractmethod
    def search(self, query: str, size: float | None = None) -> list[SneakerListing]:
        """
        Search for sneaker listings.

        Args:
            query: Search term (e.g. "Air Jordan 1 Retro High OG").
            size: Optional shoe size filter.

        Returns:
            List of SneakerListing results.
        """
        ...

    @abstractmethod
    def get_by_style_code(
        self, style_code: str, size: float | None = None
    ) -> list[SneakerListing]:
        """
        Look up a specific sneaker by its Nike style code.

        Args:
            style_code: Nike style code (e.g. "DZ5485-612").
            size: Optional shoe size filter.

        Returns:
            List of SneakerListing results.
        """
        ...
