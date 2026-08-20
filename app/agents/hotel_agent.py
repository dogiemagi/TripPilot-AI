from app.models.travel import HotelOption, TravelerPreference
from app.providers.hotel_provider import HotelProviderAggregator
from app.services.recommendation_engine import RecommendationEngine


class HotelAgent:
    def __init__(self) -> None:
        self.provider = HotelProviderAggregator()

    async def find_and_rank_hotels(
        self,
        city: str,
        nights: int = 1,
        guests: int = 1,
        min_rating: float = 0.0,
        max_price_per_night: float | None = None,
        preference: TravelerPreference | None = None,
        budget_limit: float | None = None,
    ) -> list[HotelOption]:
        dietary = preference.dietary_requirements[0] if preference and preference.dietary_requirements else None
        raw_hotels = await self.provider.search_hotels(
            city=city,
            nights=nights,
            guests=guests,
            min_rating=min_rating,
            max_price_per_night=max_price_per_night,
            dietary_preference=dietary,
        )
        ranked = RecommendationEngine.rank_hotels(
            hotels=raw_hotels,
            preference=preference,
            budget_limit=budget_limit,
        )
        return ranked
