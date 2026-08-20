import re
from typing import Any

from app.models.agent import ChatResponse, ToolCallRecord
from app.models.budget import ItemizedBudget
from app.models.travel import (
    ActivityOption,
    FlightOption,
    HotelOption,
    TravelerPreference,
    TripState,
)
from app.services.budget_engine import BudgetEngine
from app.services.context_manager import ContextManager
from app.services.memory_service import MemoryService
from app.services.rag_service import RAGPipeline

from .activity_agent import ActivityAgent
from .budget_agent import BudgetAgent
from .flight_agent import FlightAgent
from .hotel_agent import HotelAgent
from .itinerary_agent import ItineraryAgent


class Orchestrator:
    def __init__(self) -> None:
        self.flight_agent = FlightAgent()
        self.hotel_agent = HotelAgent()
        self.activity_agent = ActivityAgent()
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent()

    async def run(
        self,
        user_id: str,
        text: str,
        trip_id: str | None = None,
        profile: TravelerPreference | None = None,
        detected_landmark: str | None = None,
        intent: str = "itinerary_planning",
        confidence: float = 0.90,
    ) -> ChatResponse:
        # 1. Extract and store any new long-term preferences from the user's prompt
        MemoryService.extract_preferences_from_text(user_id, text)
        stored_pref = MemoryService.get_user_preference_profile(user_id)
        active_pref = profile or stored_pref

        # 2. Destination and budget extraction
        destinations = ["hyderabad", "paris", "dubai", "goa", "delhi", "bangalore", "chennai"]
        detected_dest = next((d.title() for d in destinations if d in text.lower()), None)

        # Budget extraction
        budget_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]{3,})", text, re.IGNORECASE)
        budget_val = float(budget_match.group(1).replace(",", "")) if budget_match else None

        # Duration extraction
        days_match = re.search(r"\b(\d+)\s*(?:-| )?day", text, re.IGNORECASE)
        duration_days = int(days_match.group(1)) if days_match else 4

        # 3. Retrieve or create trip state
        trip = ContextManager.get_or_create_trip(
            user_id=user_id,
            trip_id=trip_id,
            destination=detected_dest or (detected_landmark or "Hyderabad"),
        )
        if detected_dest:
            trip.destination = detected_dest
            trip.title = f"{detected_dest} Journey"
        if budget_val:
            trip.budget_ceiling = budget_val
        if days_match:
            trip.duration_days = duration_days

        # 4. Check conversational modifications ("Make it cheaper", "Keep hotel, change flight")
        mods = ContextManager.resolve_conversation_modifications(text, trip)

        # 5. Search travel data via Agents
        flight_options = await self.flight_agent.find_and_rank_flights(
            origin=trip.origin or "Chennai",
            destination=trip.destination,
            travelers=trip.travelers,
            preference=active_pref,
            budget_limit=trip.budget_ceiling,
        )

        hotel_options = await self.hotel_agent.find_and_rank_hotels(
            city=trip.destination,
            nights=max(1, trip.duration_days - 1),
            guests=trip.travelers,
            preference=active_pref,
            budget_limit=trip.budget_ceiling,
        )

        activity_options = await self.activity_agent.curate_activities(
            city=trip.destination,
            preference=active_pref,
        )

        # 6. Resolve selections based on state and modifications
        if mods["make_cheaper"]:
            # Pick cheaper flight and hotel
            if flight_options:
                trip.selected_flight = min(flight_options, key=lambda f: f.price.amount)
            if hotel_options:
                trip.selected_hotel = min(hotel_options, key=lambda h: h.price_per_night.amount)
        else:
            if not mods["keep_flight"] and (not trip.selected_flight or mods["change_flight"]):
                if flight_options:
                    trip.selected_flight = flight_options[0]

            if not mods["keep_hotel"] and (not trip.selected_hotel or mods["change_hotel"]):
                if hotel_options:
                    trip.selected_hotel = hotel_options[0]

        trip.selected_activities = activity_options[:3]

        # 7. Calculate itemized budget deterministically
        budget = self.budget_agent.calculate_trip_budget(
            flight=trip.selected_flight,
            hotel=trip.selected_hotel,
            activities=trip.selected_activities,
            duration_days=trip.duration_days,
            travelers=trip.travelers,
            budget_ceiling=trip.budget_ceiling,
        )

        # 8. Build Schedule via Itinerary Agent
        itinerary_days = self.itinerary_agent.build_schedule(
            destination=trip.destination,
            duration_days=trip.duration_days,
            flight=trip.selected_flight,
            hotel=trip.selected_hotel,
            activities=trip.selected_activities,
            preference=active_pref,
        )

        # 9. RAG Knowledge Retrieval
        rag_query = f"{trip.destination} {text} vegetarian food policies attractions"
        retrieved_docs = RAGPipeline.retrieve(rag_query, limit=3)
        sources = RAGPipeline.format_sources(retrieved_docs)

        # Save updated trip state
        ContextManager.save_trip(trip)

        # 10. Synthesize transparent answer
        answer = self._synthesize_answer(
            trip=trip,
            budget=budget,
            flight=trip.selected_flight,
            hotel=trip.selected_hotel,
            activities=trip.selected_activities,
            preference=active_pref,
            retrieved_docs=retrieved_docs,
            mods=mods,
        )

        return ChatResponse(
            trip_id=trip.trip_id,
            answer=answer,
            intent=intent,
            confidence=confidence,
            requires_clarification=False,
            trip_state=trip,
            budget=budget,
            flight_recommendations=flight_options[:3],
            hotel_recommendations=hotel_options[:3],
            activity_recommendations=activity_options[:4],
            itinerary_days=itinerary_days,
            retrieved_context=retrieved_docs,
            sources=sources,
            ready_to_download=True,
            model_used="trippilot-multiagent-orchestrator",
        )

    def _synthesize_answer(
        self,
        trip: TripState,
        budget: ItemizedBudget,
        flight: FlightOption | None,
        hotel: HotelOption | None,
        activities: list[ActivityOption],
        preference: TravelerPreference,
        retrieved_docs: list[dict[str, Any]],
        mods: dict[str, Any],
    ) -> str:
        lines = []

        is_veg = "vegetarian" in [d.lower() for d in preference.dietary_requirements]
        is_low_crowd = preference.crowd_preference == "low_crowds"

        pref_notes = []
        if is_veg:
            pref_notes.append("🌱 Pure Vegetarian dining prioritized")
        if is_low_crowd:
            pref_notes.append("🕊 Low-crowd heritage spots prioritized")
        pref_header = f" ({' & '.join(pref_notes)})" if pref_notes else ""

        lines.append(f"Here is your personalized {trip.duration_days}-Day {trip.destination} Travel Plan{pref_header}:\n")

        if flight:
            lines.append(f"✈️ Recommended Flight: {flight.airline} {flight.flight_number} ({flight.origin} → {flight.destination})")
            lines.append(f"   • Departure: {flight.departure_time} → Arrival: {flight.arrival_time} ({flight.duration}, Non-stop)")
            lines.append(f"   • Fare: ₹{flight.price.amount:,.0f} · Why: {flight.recommendation_reason}\n")

        if hotel:
            lines.append(f"🏨 Recommended Stay: {hotel.name} ({hotel.neighborhood})")
            lines.append(f"   • Rating: {hotel.user_rating}/10 ({hotel.star_rating}★) · {hotel.cancellation_policy}")
            lines.append(f"   • Total ({hotel.nights} nights): ₹{hotel.price_per_night.amount * hotel.nights:,.0f} (₹{hotel.price_per_night.amount:,.0f}/night) · Why: {hotel.recommendation_reason}\n")

        if activities:
            lines.append("🎟 Curated Highlights & Dining:")
            for a in activities[:3]:
                lines.append(f"   • {a.name} ({a.category}): ₹{a.price.amount:,.0f} — {a.recommendation_reason}")
            lines.append("")

        # Transparent Budget Summary
        lines.append("💰 Itemized Budget Breakdown:")
        for cat in budget.categories:
            cat_icon = {"flight": "✈️", "hotel": "🏨", "food": "🍛", "local_transportation": "🚕", "activities": "🎟", "insurance": "🛡"}.get(cat.category, "📦")
            lines.append(f"   • {cat_icon} {cat.category.replace('_', ' ').title():<22} ₹{cat.subtotal:>8,.0f}")
        lines.append(f"   {'—'*34}")
        lines.append(f"   • GRAND TOTAL             ₹{budget.grand_total:>8,.0f}")

        if budget.budget_ceiling:
            if budget.is_over_budget:
                lines.append(f"\n⚠️ Budget Alert: Plan is ₹{budget.overage_amount:,.0f} over your ₹{budget.budget_ceiling:,.0f} ceiling.")
                if budget.reduction_suggestions:
                    lines.append("💡 Suggested Reductions:")
                    for idx, s in enumerate(budget.reduction_suggestions, 1):
                        lines.append(f"   {idx}. {s.action} → Save ₹{s.estimated_saving:,.0f} ({s.description})")
            else:
                lines.append(f"   • Budget Ceiling: ₹{budget.budget_ceiling:,.0f} (Remaining Buffer: ₹{budget.remaining_budget:,.0f})")

        return "\n".join(lines)

