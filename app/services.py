import json
import re
import sqlite3
from pathlib import Path

from .models import Candidate, TravelerProfile

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "trippilot.db"

INTENT_KEYWORDS = {
    "hotel_search": ("hotel", "stay", "accommodation", "hostel"),
    "itinerary_generation": ("plan", "itinerary", "day trip", "days"),
    "budget_planning": ("budget", "cheap", "cost", "under", "afford"),
    "food_recommendation": ("food", "restaurant", "eat", "vegetarian", "cafe"),
    "weather_query": ("weather", "rain", "temperature", "forecast"),
    "destination_info": ("nearby", "visit", "what is", "landmark", "place"),
    "transport_search": ("flight", "train", "transport", "airport", "metro"),
}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZÀ-ÿ']+", text.lower()))


def detect_intent(text: str) -> tuple[str, float]:
    words = tokens(text)
    matches = {name: len(words.intersection(keys)) for name, keys in INTENT_KEYWORDS.items()}
    intent, count = max(matches.items(), key=lambda item: item[1])
    return (intent if count else "general_travel", min(0.98, 0.55 + count * 0.15))


def retrieve(query: str, limit: int = 3) -> list[dict]:
    records = json.loads((DATA_DIR / "travel_knowledge.json").read_text(encoding="utf-8"))
    query_terms = tokens(query)
    ranked = []
    for record in records:
        score = len(query_terms.intersection(tokens(" ".join(record.values()))))
        if score:
            ranked.append((score, record))
    return [record for _, record in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]


def initialize_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS memories (user_id TEXT, kind TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def store_memory(user_id: str, kind: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO memories (user_id, kind, content) VALUES (?, ?, ?)", (user_id, kind, content[:4000]))


def get_memories(user_id: str, limit: int = 5) -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT content FROM memories WHERE user_id = ? ORDER BY rowid DESC LIMIT ?", (user_id, limit)).fetchall()
    return [row[0] for row in rows]


def score_candidate(candidate: Candidate) -> dict:
    weights = {"price_score": .30, "location_score": .25, "rating_score": .20, "preference_score": .15, "amenities_score": .10}
    score = sum(getattr(candidate, key) * weight for key, weight in weights.items())
    reasons = [key.removesuffix("_score").replace("_", " ") for key, weight in weights.items() if getattr(candidate, key) >= .75]
    return {"name": candidate.name, "score": round(score * 100, 1), "strengths": reasons}


def compose_answer(text: str, intent: str, landmark: str | None, context: list[dict], memories: list[str], profile: TravelerProfile | None) -> str:
    destination = landmark or (context[0]["destination"] if context else None)
    subject = destination or "your destination"
    if intent == "itinerary_generation":
        answer = f"Here is a flexible plan for {subject}: start with one anchor attraction each morning, cluster nearby sights in the afternoon, and reserve evenings for neighbourhood food. I can refine it once you share dates, budget, and pace."
    elif intent == "hotel_search":
        answer = f"For {subject}, prioritize accommodation near transit and compare the total price (including taxes), cancellation terms, and recent reviews. I can rank options if you provide candidates or a budget."
    elif intent == "food_recommendation":
        diet = ", ".join(profile.dietary_requirements) if profile and profile.dietary_requirements else "your dietary preferences"
        answer = f"Around {subject}, look for well-reviewed local spots and confirm {diet} options before going."
    elif intent == "weather_query":
        answer = "I can help interpret a forecast, but live weather needs a connected weather provider. Share the city and dates for a packing checklist."
    else:
        answer = f"Great choice - I can build a trip to {subject}. Reply with your departure date, total budget, number of days, and preferred transport (flight, train, bus, or car)."
    if landmark:
        answer = f"I identified the supplied context as **{landmark}**. {answer}"
    return answer


def build_trip_plan(conversation: str, context: list[dict]) -> tuple[str, list[str]] | None:
    """Turn a short planning conversation into a transparent, offline itinerary."""
    text = conversation.lower()
    destinations = ("paris", "dubai", "goa")
    destination = next((name.title() for name in destinations if name in text), None)
    budget_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]{3,})", conversation, re.IGNORECASE)
    date_match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", conversation)
    transport = next((mode for mode in ("flight", "train", "bus", "car") if re.search(rf"\b{mode}\b", text)), None)
    if not (destination and budget_match and date_match and transport):
        return None

    budget = budget_match.group(1)
    highlights = {
        "Paris": ["Eiffel Tower and Trocadéro", "Louvre and the Seine", "Montmartre and a local bistro"],
        "Dubai": ["Old Dubai and Al Fahidi", "Burj Khalifa and Dubai Mall", "Jumeirah Beach or a desert evening"],
        "Goa": ["A relaxed beach morning", "Fontainhas heritage walk", "A coastal café and sunset"],
    }[destination]
    plan = (
        f"Trip brief: {destination}\n"
        f"Departure date: {date_match.group(0)}\n"
        f"Budget ceiling: ₹{budget}\n"
        f"Preferred transport: {transport.title()}\n\n"
        f"Day 1 - {highlights[0]}\nStart with the main landmark, then choose a nearby meal and keep the evening flexible.\n\n"
        f"Day 2 - {highlights[1]}\nBook your anchor attraction in advance and group nearby sights to reduce travel time.\n\n"
        f"Day 3 - {highlights[2]}\nUse this day for neighbourhood exploration, food, and a low-pressure finish.\n\n"
        "Budget approach\nReserve roughly 45% for travel and stay, 30% for activities and food, and keep 25% as a buffer. Compare live prices before booking."
    )
    sources = [f"Destination: {destination}", f"Departure: {date_match.group(0)}", f"Budget: ₹{budget}", f"Transport: {transport.title()}"]
    sources.extend(f"{item['topic']}: {item['content']}" for item in context)
    return plan, sources
