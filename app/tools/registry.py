from typing import Any, Callable, Coroutine
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: dict[str, Any]


class SearchFlightsArgs(BaseModel):
    origin: str = Field(description="Origin city, e.g. Chennai, Delhi, Mumbai")
    destination: str = Field(description="Destination city, e.g. Hyderabad, Paris, Goa")
    date: str | None = Field(default=None, description="Departure date (YYYY-MM-DD)")
    travelers: int = Field(default=1, ge=1, le=10)
    cabin_class: str = Field(default="Economy")


class SearchHotelsArgs(BaseModel):
    city: str = Field(description="Destination city")
    nights: int = Field(default=1, ge=1, le=30)
    guests: int = Field(default=1, ge=1)
    min_rating: float = Field(default=0.0, ge=0, le=10)
    max_price_per_night: float | None = None
    dietary_preference: str | None = None


class SearchActivitiesArgs(BaseModel):
    city: str = Field(description="City to explore")
    category: str | None = None
    dietary_tags: list[str] | None = None
    crowd_preference: str | None = None


class CalculateBudgetArgs(BaseModel):
    duration_days: int = Field(default=3, ge=1)
    travelers: int = Field(default=1, ge=1)
    budget_ceiling: float | None = None


class GetWeatherArgs(BaseModel):
    city: str
    date: str | None = None


class SearchKnowledgeArgs(BaseModel):
    query: str
    limit: int = Field(default=3, ge=1, le=10)


TOOL_DEFINITIONS = [
    ToolDefinition(
        name="search_flights",
        description="Search real-time or catalog flights between city pairs with pricing and schedule details.",
        parameters_schema=SearchFlightsArgs.model_json_schema(),
    ),
    ToolDefinition(
        name="search_hotels",
        description="Search accommodation options in destination city with star ratings, pricing, and amenities.",
        parameters_schema=SearchHotelsArgs.model_json_schema(),
    ),
    ToolDefinition(
        name="search_activities",
        description="Find attractions, cultural heritage walks, and dining options with crowd levels and dietary tags.",
        parameters_schema=SearchActivitiesArgs.model_json_schema(),
    ),
    ToolDefinition(
        name="calculate_budget",
        description="Deterministically calculate total and itemized daily travel budget across all selected components.",
        parameters_schema=CalculateBudgetArgs.model_json_schema(),
    ),
    ToolDefinition(
        name="get_weather",
        description="Retrieve weather forecast and packing recommendations for a destination.",
        parameters_schema=GetWeatherArgs.model_json_schema(),
    ),
    ToolDefinition(
        name="search_knowledge",
        description="Retrieve policy, visa, cancellation, and destination guides via RAG.",
        parameters_schema=SearchKnowledgeArgs.model_json_schema(),
    ),
]
