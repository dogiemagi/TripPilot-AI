import re
from app.models.agent import IntentResult


CLARIFICATION_PATTERNS = [
    (
        r"^(?:find|get|show|book)\s+(?:something|anything)\s+(?:cheap|affordable|budget)\s*(?:for\s+tomorrow|soon)?$",
        "Would you like me to find a cheap flight, a hotel stay, or activities for your trip?",
    ),
    (
        r"^(?:help|travel|plan)\s*$",
        "Where would you like to travel, and for how many days? Share your destination and budget.",
    ),
]


INTENT_KEYWORDS = {
    "flight_search": (
        "flight", "flights", "airline", "airlines", "fly", "flying", "ticket", "tickets",
        "airport", "airports", "plane", "planes", "airfare", "airfares"
    ),
    "hotel_search": (
        "hotel", "hotels", "stay", "stays", "accommodation", "accommodations",
        "resort", "resorts", "hostel", "hostels", "room", "rooms", "lodging"
    ),
    "activity_search": (
        "activity", "activities", "places", "attraction", "attractions", "sightseeing",
        "things to do", "monument", "monuments", "temple", "temples", "museum", "museums"
    ),
    "itinerary_planning": (
        "plan", "itinerary", "itineraries", "day trip", "days trip", "trip to", "tour",
        "vacation", "holiday"
    ),
    "budget_optimization": (
        "cheaper", "reduce budget", "save money", "lower cost", "over budget",
        "reduce cost", "less expensive", "cut cost"
    ),
    "booking": (
        "book", "booking", "reserve", "reservation", "confirm booking", "add to cart",
        "proceed to book"
    ),
    "travel_policy": (
        "baggage", "luggage", "cancellation policy", "cancellation", "visa",
        "entry requirements", "refund", "terms"
    ),
    "general_travel": (
        "weather", "packing", "advice", "hello", "hi", "recommend", "guide"
    ),
}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9À-ÿ']+", text.lower()))


class ConfidenceEvaluator:
    CLARIFICATION_THRESHOLD = 0.65

    @classmethod
    def evaluate_intent(cls, text: str) -> IntentResult:
        clean_text = text.strip()
        low_text = clean_text.lower()

        # 1. Check direct ambiguity patterns
        for pat, clarification_msg in CLARIFICATION_PATTERNS:
            if re.search(pat, low_text, re.IGNORECASE):
                return IntentResult(
                    intent="ambiguous_query",
                    confidence=0.45,
                    requires_clarification=True,
                    clarification_prompt=clarification_msg,
                    rationale="Input lacks specific travel entity (flight, hotel, or destination).",
                )

        # 2. Extract entities
        extracted: dict[str, str | float] = {}
        dest_match = re.search(r"\b(hyderabad|paris|dubai|goa|delhi|mumbai|bangalore|chennai)\b", low_text)
        if dest_match:
            extracted["destination"] = dest_match.group(1).title()

        budget_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]{3,})", text, re.IGNORECASE)
        if budget_match:
            extracted["budget"] = float(budget_match.group(1).replace(",", ""))

        days_match = re.search(r"\b(\d+)\s*(?:-| )?day", low_text)
        if days_match:
            extracted["days"] = int(days_match.group(1))

        # 3. Match keyword intents
        words = tokens(clean_text)
        scores: dict[str, int] = {}
        for intent_name, keys in INTENT_KEYWORDS.items():
            overlap = len(words.intersection(keys))
            scores[intent_name] = overlap

        best_intent, match_count = max(scores.items(), key=lambda item: item[1])

        # If user explicitly asked for hotels or flights alone, prioritize that intent
        if scores.get("hotel_search", 0) > 0 and scores.get("itinerary_planning", 0) == 0:
            best_intent = "hotel_search"
            confidence = min(0.95, 0.65 + scores["hotel_search"] * 0.15)
        elif scores.get("flight_search", 0) > 0 and scores.get("itinerary_planning", 0) == 0:
            best_intent = "flight_search"
            confidence = min(0.95, 0.65 + scores["flight_search"] * 0.15)
        elif extracted.get("destination") and not extracted.get("days") and not extracted.get("budget") and len(clean_text.split()) < 10 and scores.get("flight_search", 0) == 0 and scores.get("hotel_search", 0) == 0:
            dest = extracted["destination"]
            return IntentResult(
                intent="itinerary_planning",
                confidence=0.55,
                requires_clarification=True,
                clarification_prompt=(
                    f"I would love to help you plan your trip to {dest}! To give you an exact itemized budget and customized itinerary, could you let me know:\n"
                    f"1. How many days will you be visiting {dest}?\n"
                    f"2. What is your approximate budget (e.g. ₹20,000)?\n"
                    f"3. Do you have any dietary preferences (such as Pure Vegetarian) or crowd preferences (such as Quiet/Low Crowds)?\n"
                    f"4. What is your departure city for flights/travel?"
                ),
                extracted_entities=extracted,
                rationale=f"Destination {dest} detected without duration or budget; requesting clarification.",
            )
        elif extracted.get("destination") and (extracted.get("days") or extracted.get("budget")):
            best_intent = "itinerary_planning"
            confidence = 0.94
        elif match_count > 0:
            confidence = min(0.92, 0.60 + (match_count * 0.12))
        else:
            best_intent = "general_travel"
            confidence = 0.58


        requires_clarification = confidence < cls.CLARIFICATION_THRESHOLD
        clarification_prompt = None
        if requires_clarification:
            clarification_prompt = (
                "Could you specify your destination, dates, and whether you are looking for flights, hotels, or a full itinerary?"
            )

        return IntentResult(
            intent=best_intent,
            confidence=round(confidence, 2),
            requires_clarification=requires_clarification,
            clarification_prompt=clarification_prompt,
            extracted_entities=extracted,
            rationale=f"Classified as {best_intent} with {match_count} keyword matches.",
        )
