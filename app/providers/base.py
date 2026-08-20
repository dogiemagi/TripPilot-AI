from abc import ABC, abstractmethod
from typing import Any

from app.models.travel import ActivityOption, FlightOption, HotelOption


class FlightProvider(ABC):
    @abstractmethod
    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: str | None = None,
        travelers: int = 1,
        cabin_class: str = "Economy",
    ) -> list[FlightOption]:
        """Search flight options across carriers."""
        pass


class HotelProvider(ABC):
    @abstractmethod
    async def search_hotels(
        self,
        city: str,
        nights: int = 1,
        guests: int = 1,
        min_rating: float = 0.0,
        max_price_per_night: float | None = None,
        dietary_preference: str | None = None,
    ) -> list[HotelOption]:
        """Search hotel options in destination city."""
        pass


class ActivityProvider(ABC):
    @abstractmethod
    async def search_activities(
        self,
        city: str,
        category: str | None = None,
        dietary_tags: list[str] | None = None,
        crowd_preference: str | None = None,
    ) -> list[ActivityOption]:
        """Search curated attractions, dining, and activities."""
        pass


class WeatherProvider(ABC):
    @abstractmethod
    async def get_forecast(
        self,
        city: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Get forecast details for travel planning."""
        pass
