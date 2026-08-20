import os
from typing import Literal
from pydantic import BaseModel


class ModelProfile(BaseModel):
    model_id: str
    provider: Literal["google", "openai", "local", "deterministic"]
    task_suitability: list[str]
    cost_per_1k_tokens: float
    avg_latency_ms: float
    supports_vision: bool = False
    supports_tools: bool = False


MODEL_REGISTRY: dict[str, ModelProfile] = {
    "gemini-flash": ModelProfile(
        model_id="gemini-1.5-flash",
        provider="google",
        task_suitability=["general_chat", "intent_classification", "fast_summarization"],
        cost_per_1k_tokens=0.00035,
        avg_latency_ms=450.0,
        supports_vision=True,
        supports_tools=True,
    ),
    "gemini-pro": ModelProfile(
        model_id="gemini-1.5-pro",
        provider="google",
        task_suitability=["complex_itinerary_planning", "multi_agent_orchestration"],
        cost_per_1k_tokens=0.0035,
        avg_latency_ms=1200.0,
        supports_vision=True,
        supports_tools=True,
    ),
    "gpt-4o-mini": ModelProfile(
        model_id="gpt-4o-mini",
        provider="openai",
        task_suitability=["intent_classification", "tool_routing"],
        cost_per_1k_tokens=0.00015,
        avg_latency_ms=380.0,
        supports_vision=True,
        supports_tools=True,
    ),
    "trippilot-deterministic": ModelProfile(
        model_id="trippilot-deterministic-engine",
        provider="deterministic",
        task_suitability=["all_travel_workflows", "zero_cost_fallback"],
        cost_per_1k_tokens=0.0,
        avg_latency_ms=12.0,
        supports_vision=True,
        supports_tools=True,
    ),
}


def get_available_ai_provider() -> str:
    if os.getenv("GEMINI_API_KEY"):
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "deterministic"
