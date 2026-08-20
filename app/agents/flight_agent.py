from app.models.travel import FlightOption, TravelerPreference
from app.providers.flight_provider import FlightProviderAggregator
from app.services.recommendation_engine import RecommendationEngine


class FlightAgent:
    def __init__(self) -> None:
        self.provider = FlightProviderAggregator()

    async def find_and_rank_flights(
        self,
        origin: str,
        destination: str,
        date: str | None = None,
        travelers: int = 1,
        cabin_class: str = "Economy",
        preference: TravelerPreference | None = None,
        budget_limit: float | None = None,
    ) -> list[FlightOption]:
        raw_flights = await self.provider.search_flights(
            origin=origin,
            destination=destination,
            date=date,
            travelers=travelers,
            cabin_class=cabin_class,
        )
        ranked = RecommendationEngine.rank_flights(
            flights=raw_flights,
            preference=preference,
            budget_limit=budget_limit,
        )
        return ranked
