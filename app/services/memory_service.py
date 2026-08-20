import re
from datetime import datetime, timezone
from app.database import get_db_connection
from app.models.travel import TravelerPreference


class MemoryService:
    @staticmethod
    def store_memory(
        user_id: str,
        category: str,
        preference_key: str,
        preference_value: str,
        confidence: float = 0.9,
        source: str = "conversation",
    ) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (user_id, category, preference_key, preference_value, confidence, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(user_id, preference_key) DO UPDATE SET
                    preference_value = excluded.preference_value,
                    confidence = excluded.confidence,
                    updated_at = datetime('now')
                """,
                (user_id, category, preference_key, preference_value, confidence, source),
            )

    @staticmethod
    def retrieve_memories(user_id: str) -> list[dict]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT category, preference_key, preference_value, confidence, source, created_at, updated_at
                FROM memories
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_user_preference_profile(user_id: str) -> TravelerPreference:
        memories = MemoryService.retrieve_memories(user_id)
        pref = TravelerPreference()
        for m in memories:
            key = m["preference_key"]
            val = m["preference_value"]
            if key == "dietary_requirement" and val not in pref.dietary_requirements:
                pref.dietary_requirements.append(val)
            elif key == "crowd_preference" and val in ("low_crowds", "moderate", "any"):
                pref.crowd_preference = val
            elif key == "preferred_airline" and val not in pref.preferred_airlines:
                pref.preferred_airlines.append(val)
            elif key == "seat_preference":
                pref.seat_preference = val
        return pref

    @staticmethod
    def delete_memory(user_id: str, preference_key: str | None = None) -> None:
        with get_db_connection() as conn:
            if preference_key:
                conn.execute(
                    "DELETE FROM memories WHERE user_id = ? AND preference_key = ?",
                    (user_id, preference_key),
                )
            else:
                conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))

    @staticmethod
    def extract_preferences_from_text(user_id: str, text: str) -> list[dict]:
        """Rule-based preference extractor with confidence calibration."""
        extracted = []
        low_text = text.lower()

        # Dietary preferences
        if re.search(r"\b(pure veg|vegetarian|veg food|no meat|veg only)\b", low_text):
            MemoryService.store_memory(user_id, "dietary", "dietary_requirement", "vegetarian", 0.95)
            extracted.append({"key": "dietary_requirement", "value": "vegetarian", "confidence": 0.95})
        elif re.search(r"\b(vegan|plant based)\b", low_text):
            MemoryService.store_memory(user_id, "dietary", "dietary_requirement", "vegan", 0.95)
            extracted.append({"key": "dietary_requirement", "value": "vegan", "confidence": 0.95})

        # Crowd preferences
        if re.search(r"\b(less crowd|less crowded|quiet|peaceful|secluded|avoid crowd)\b", low_text):
            MemoryService.store_memory(user_id, "travel_style", "crowd_preference", "low_crowds", 0.92)
            extracted.append({"key": "crowd_preference", "value": "low_crowds", "confidence": 0.92})

        # Airlines
        if "indigo" in low_text:
            MemoryService.store_memory(user_id, "airline", "preferred_airline", "IndiGo", 0.88)
            extracted.append({"key": "preferred_airline", "value": "IndiGo", "confidence": 0.88})
        elif "air india" in low_text:
            MemoryService.store_memory(user_id, "airline", "preferred_airline", "Air India", 0.88)
            extracted.append({"key": "preferred_airline", "value": "Air India", "confidence": 0.88})

        return extracted
