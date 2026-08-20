from app.models.travel import ActivityOption, TravelerPreference
from app.providers.activity_provider import ActivityProviderAggregator
from app.services.recommendation_engine import RecommendationEngine


class ActivityAgent:
    def __init__(self) -> None:
        self.provider = ActivityProviderAggregator()

    async def curate_activities(
        self,
        city: str,
        category: str | None = None,
        preference: TravelerPreference | None = None,
    ) -> list[ActivityOption]:
        dietary_tags = preference.dietary_requirements if preference else None
        crowd_pref = preference.crowd_preference if preference else None

        raw_activities = await self.provider.search_activities(
            city=city,
            category=category,
            dietary_tags=dietary_tags,
            crowd_preference=crowd_pref,
        )
        ranked = RecommendationEngine.rank_activities(
            activities=raw_activities,
            preference=preference,
        )
        return ranked
