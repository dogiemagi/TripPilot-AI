import pytest
from app.database import init_db
from app.models.travel import TripState
from app.services.context_manager import ContextManager
from app.services.memory_service import MemoryService


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_preference_extraction_and_storage():
    user_id = "test-user-pref-1"
    MemoryService.delete_memory(user_id)

    text = "I prefer vegetarian food and less crowded spots, flying with IndiGo."
    extracted = MemoryService.extract_preferences_from_text(user_id, text)
    assert len(extracted) >= 2

    profile = MemoryService.get_user_preference_profile(user_id)
    assert "vegetarian" in profile.dietary_requirements
    assert profile.crowd_preference == "low_crowds"
    assert "IndiGo" in profile.preferred_airlines


def test_context_modification_resolution():
    trip = TripState(
        trip_id="trip-ctx-test",
        user_id="user-ctx-test",
        destination="Hyderabad",
    )

    mods = ContextManager.resolve_conversation_modifications("Make it cheaper", trip)
    assert mods["make_cheaper"] is True

    mods2 = ContextManager.resolve_conversation_modifications("Keep the hotel but change the flight", trip)
    assert mods2["keep_hotel"] is True
    assert mods2["change_flight"] is True
