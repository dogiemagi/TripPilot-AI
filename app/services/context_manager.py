import json
import re
import uuid
from datetime import datetime, timezone
from app.database import get_db_connection
from app.models.travel import (
    ActivityOption,
    CartItem,
    FlightOption,
    HotelOption,
    TravelerPreference,
    TripState,
)
from app.services.memory_service import MemoryService


class ContextManager:
    """Manages multi-turn conversation, trip state, persistent user preferences, and decision history."""

    @staticmethod
    def get_or_create_trip(user_id: str, trip_id: str | None = None, destination: str = "Hyderabad") -> TripState:
        with get_db_connection() as conn:
            if trip_id:
                row = conn.execute("SELECT state_json FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
                if row:
                    data = json.loads(row["state_json"])
                    return TripState.model_validate(data)

            # Look up active trip in user's latest session
            sess_row = conn.execute(
                "SELECT active_trip_id FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if sess_row and sess_row["active_trip_id"]:
                trip_row = conn.execute(
                    "SELECT state_json FROM trips WHERE trip_id = ?",
                    (sess_row["active_trip_id"],),
                ).fetchone()
                if trip_row:
                    return TripState.model_validate(json.loads(trip_row["state_json"]))

            # Create new trip
            new_id = f"trip-{uuid.uuid4().hex[:8]}"
            trip = TripState(
                trip_id=new_id,
                user_id=user_id,
                title=f"{destination.title()} Trip",
                destination=destination.title(),
                origin="Chennai",
                duration_days=4 if "hyderabad" in destination.lower() else 3,
                budget_ceiling=20000.0 if "hyderabad" in destination.lower() else None,
            )
            ContextManager.save_trip(trip)
            return trip

    @staticmethod
    def save_trip(trip: TripState) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO trips (trip_id, user_id, title, destination, origin, start_date, duration_days, travelers, budget_ceiling, state_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(trip_id) DO UPDATE SET
                    title = excluded.title,
                    destination = excluded.destination,
                    origin = excluded.origin,
                    start_date = excluded.start_date,
                    duration_days = excluded.duration_days,
                    travelers = excluded.travelers,
                    budget_ceiling = excluded.budget_ceiling,
                    state_json = excluded.state_json,
                    updated_at = datetime('now')
                """,
                (
                    trip.trip_id,
                    trip.user_id,
                    trip.title,
                    trip.destination,
                    trip.origin,
                    trip.start_date,
                    trip.duration_days,
                    trip.travelers,
                    trip.budget_ceiling,
                    trip.model_dump_json(),
                ),
            )

    @staticmethod
    def update_session(session_id: str, user_id: str, active_trip_id: str | None = None) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, active_trip_id, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(session_id) DO UPDATE SET
                    active_trip_id = COALESCE(excluded.active_trip_id, sessions.active_trip_id),
                    updated_at = datetime('now')
                """,
                (session_id, user_id, active_trip_id),
            )

    @staticmethod
    def log_message(session_id: str, role: str, content: str, intent: str | None = None, confidence: float | None = None) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, intent, confidence) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, intent, confidence),
            )

    @staticmethod
    def get_recent_messages(session_id: str, limit: int = 6) -> list[dict]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT role, content, intent, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]

    @staticmethod
    def resolve_conversation_modifications(
        text: str, trip: TripState
    ) -> dict[str, bool | str]:
        """Detect conversational modifications like:

        'Make it cheaper', 'Keep the hotel but change the flight',
        'Add hotel to cart', 'Add activity'.
        """
        low = text.lower()
        mods = {
            "make_cheaper": bool(re.search(r"\b(cheaper|reduce cost|lower budget|less expensive|save money|cut cost)\b", low)),
            "change_flight": bool(re.search(r"\b(change\s+(?:the\s+)?flight|different\s+(?:the\s+)?flight|other\s+flight|switch\s+(?:the\s+)?flight)\b", low)),
            "change_hotel": bool(re.search(r"\b(change\s+(?:the\s+)?hotel|different\s+(?:the\s+)?hotel|other\s+hotel|switch\s+(?:the\s+)?hotel)\b", low)),
            "keep_hotel": bool(re.search(r"\b(keep\s+(?:the\s+)?hotel|same\s+hotel|stay\s+at\s+(?:the\s+)?hotel)\b", low)),
            "keep_flight": bool(re.search(r"\b(keep\s+(?:the\s+)?flight|same\s+flight)\b", low)),
            "select_item": None,
        }

        # Cart selection pattern: "Add the second hotel to my trip" or "Select hotel 1"
        hotel_match = re.search(r"\b(?:add|select|choose|pick)\s+(?:the\s+)?(first|second|third|1st|2nd|3rd|\d+)\s+hotel\b", low)
        if hotel_match:
            mods["select_item"] = f"hotel:{hotel_match.group(1)}"

        flight_match = re.search(r"\b(?:add|select|choose|pick)\s+(?:the\s+)?(first|second|third|1st|2nd|3rd|\d+)\s+flight\b", low)
        if flight_match:
            mods["select_item"] = f"flight:{flight_match.group(1)}"

        return mods
