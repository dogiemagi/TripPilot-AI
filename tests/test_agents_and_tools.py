import pytest
from app.agents.orchestrator import Orchestrator
from app.database import init_db
from app.models.travel import TravelerPreference
from app.tools.executor import ToolExecutor


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.mark.asyncio
async def test_tool_executor():
    executor = ToolExecutor()
    res = await executor.execute_tool(
        "search_flights",
        {"origin": "Chennai", "destination": "Hyderabad", "travelers": 1},
    )
    assert res.status == "success"
    assert res.result["count"] > 0
    assert len(res.result["flights"]) > 0


@pytest.mark.asyncio
async def test_orchestrator_complete_hyderabad_scenario():
    orchestrator = Orchestrator()
    pref = TravelerPreference(
        dietary_requirements=["vegetarian"],
        crowd_preference="low_crowds",
    )

    prompt = "I'm going to Hyderabad for 4 days with a ₹20,000 budget. I prefer vegetarian food and less crowded places."
    response = await orchestrator.run(
        user_id="test-e2e-user",
        text=prompt,
        profile=pref,
    )

    assert response.trip_state is not None
    assert response.trip_state.destination == "Hyderabad"
    assert response.budget is not None
    assert response.budget.grand_total > 0
    assert response.budget.grand_total <= 20000.0 or response.budget.is_over_budget
    assert len(response.flight_recommendations) > 0
    assert len(response.hotel_recommendations) > 0
    assert len(response.activity_recommendations) > 0
    assert len(response.itinerary_days) == 4
    assert response.ready_to_download is True
