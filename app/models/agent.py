from typing import Literal
from pydantic import BaseModel, Field

from .budget import ItemizedBudget
from .travel import ActivityOption, FlightOption, HotelOption, TravelerPreference, TripState


class IntentResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_clarification: bool = False
    clarification_prompt: str | None = None
    extracted_entities: dict = Field(default_factory=dict)
    rationale: str = ""


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    result: dict | None = None
    status: Literal["success", "error", "skipped"] = "success"
    latency_ms: float = 0.0
    error_message: str | None = None


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=4000)
    trip_id: str | None = None
    profile: TravelerPreference | None = None
    detected_landmark: str | None = None
    modality: Literal["text", "image", "audio", "video"] = "text"


class ChatResponse(BaseModel):
    trip_id: str | None = None
    answer: str
    intent: str
    confidence: float
    requires_clarification: bool = False
    clarification_prompt: str | None = None
    trip_state: TripState | None = None
    budget: ItemizedBudget | None = None
    flight_recommendations: list[FlightOption] = Field(default_factory=list)
    hotel_recommendations: list[HotelOption] = Field(default_factory=list)
    activity_recommendations: list[ActivityOption] = Field(default_factory=list)
    itinerary_days: list[dict] = Field(default_factory=list)
    retrieved_context: list[dict] = Field(default_factory=list)
    model_used: str = "trippilot-router"
    sources: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    ready_to_download: bool = False
