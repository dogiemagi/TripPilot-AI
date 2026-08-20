import re
from typing import Any

from app.database import DB_PATH, DATA_DIR, get_db_connection, init_db
from app.models.budget import BudgetItem, ItemizedBudget
from app.models.legacy import Candidate, TravelerProfile
from app.models.travel import TravelerPreference
from .budget_engine import BudgetEngine
from .cache_service import CacheService
from .commerce_service import CommerceService
from .context_manager import ContextManager
from .guardrails import Guardrails
from .memory_service import MemoryService
from .multimodal_service import MultimodalGateway
from .observability import ObservabilityService
from .rag_service import RAGPipeline
from .recommendation_engine import RecommendationEngine


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZÀ-ÿ']+", text.lower()))


def detect_intent(text: str) -> tuple[str, float]:
    from app.inference.confidence import ConfidenceEvaluator
    res = ConfidenceEvaluator.evaluate_intent(text)
    return res.intent, res.confidence


def retrieve(query: str, limit: int = 3) -> list[dict[str, Any]]:
    return RAGPipeline.retrieve(query, limit=limit)


def initialize_db() -> None:
    init_db()


def purge_expired_memories() -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM memories WHERE updated_at < datetime('now', '-30 days')")


def delete_memories(session_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM memories WHERE user_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


def store_memory(user_id: str, kind: str, content: str) -> None:
    MemoryService.store_memory(
        user_id=user_id,
        category="session",
        preference_key=f"{kind}_{content[:20]}",
        preference_value=content[:4000],
        confidence=0.9,
    )


def get_memories(user_id: str, limit: int = 5) -> list[str]:
    memories = MemoryService.retrieve_memories(user_id)
    return [m["preference_value"] for m in memories[:limit]]


def score_candidate(candidate: Candidate) -> dict:
    weights = {
        "price_score": 0.30,
        "location_score": 0.25,
        "rating_score": 0.20,
        "preference_score": 0.15,
        "amenities_score": 0.10,
    }
    score = sum(getattr(candidate, key) * weight for key, weight in weights.items())
    reasons = [
        key.removesuffix("_score").replace("_", " ")
        for key, weight in weights.items()
        if getattr(candidate, key) >= 0.75
    ]
    return {"name": candidate.name, "score": round(score * 100, 1), "strengths": reasons}


def compose_answer(
    text: str,
    intent: str,
    landmark: str | None,
    context: list[dict],
    memories: list[str],
    profile: TravelerProfile | TravelerPreference | None,
) -> str:
    destination = landmark or (context[0].get("destination") if context else "Hyderabad")
    subject = destination or "your destination"

    if intent == "itinerary_planning" or intent == "itinerary_generation":
        answer = f"Here is a comprehensive, itemized travel plan for {subject}: starting with anchor attractions, transparent hotel selections, and daily meal allocations."
    elif intent == "hotel_search":
        answer = f"For {subject}, I have ranked accommodation by price, distance to central landmarks, and dietary amenities."
    elif intent == "food_recommendation":
        answer = f"Around {subject}, authentic vegetarian spots and regional dining have been prioritized."
    elif intent == "weather_query":
        answer = f"Packing checklist for {subject}: light breathable cottons, sunglasses, and comfortable walking shoes."
    else:
        answer = f"I am ready to plan your trip to {subject}. You can customize flights, stays, activities, and budget conversationally."

    if landmark:
        answer = f"I identified the supplied context as **{landmark}**. {answer}"
    return answer


def build_trip_plan(conversation: str, context: list[dict]) -> tuple[str, list[str]] | None:
    text = conversation.lower()
    destinations = ("hyderabad", "paris", "dubai", "goa", "delhi", "bangalore")
    destination = next((name.title() for name in destinations if name in text), None)
    budget_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]{3,})", conversation, re.IGNORECASE)
    date_match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", conversation)
    transport = next((mode for mode in ("flight", "train", "bus", "car") if re.search(rf"\b{mode}\b", text)), "Flight")

    if not destination:
        return None

    budget = budget_match.group(1) if budget_match else "20,000"
    date_str = date_match.group(0) if date_match else "Upcoming Weekend"

    highlights_map = {
        "Hyderabad": ["Golconda Fort & Paigah Tombs", "Chutneys Vegetarian Feast & Charminar", "Qutb Shahi Tombs Heritage Walk"],
        "Paris": ["Eiffel Tower and Trocadéro", "Louvre and the Seine", "Montmartre and a local bistro"],
        "Dubai": ["Old Dubai and Al Fahidi", "Burj Khalifa and Dubai Mall", "Jumeirah Beach or a desert evening"],
        "Goa": ["A relaxed beach morning", "Fontainhas heritage walk", "A coastal café and sunset"],
    }
    highlights = highlights_map.get(destination, [f"Day 1 in {destination}", f"Day 2 in {destination}", f"Day 3 in {destination}"])

    plan = (
        f"Trip brief: {destination}\n"
        f"Departure date: {date_str}\n"
        f"Budget ceiling: ₹{budget}\n"
        f"Preferred transport: {transport.title()}\n\n"
        f"Day 1 - {highlights[0]}\nStart with the main landmark, then choose a nearby meal and keep the evening flexible.\n\n"
        f"Day 2 - {highlights[1]}\nBook your anchor attraction in advance and group nearby sights to reduce travel time.\n\n"
        f"Day 3 - {highlights[2]}\nUse this day for neighbourhood exploration, food, and a low-pressure finish.\n\n"
        "Budget approach\nDeterministic itemized calculation with transparent daily costs."
    )
    sources = [f"Destination: {destination}", f"Departure: {date_str}", f"Budget: ₹{budget}", f"Transport: {transport.title()}"]
    sources.extend(f"{item.get('topic', 'Topic')}: {item.get('content', '')}" for item in context)
    return plan, sources


__all__ = [
    "BudgetEngine",
    "CacheService",
    "CommerceService",
    "ContextManager",
    "Guardrails",
    "MemoryService",
    "MultimodalGateway",
    "ObservabilityService",
    "RAGPipeline",
    "RecommendationEngine",
    "detect_intent",
    "retrieve",
    "initialize_db",
    "purge_expired_memories",
    "delete_memories",
    "store_memory",
    "get_memories",
    "score_candidate",
    "compose_answer",
    "build_trip_plan",
]
