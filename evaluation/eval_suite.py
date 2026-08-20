import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.flight_agent import FlightAgent
from app.agents.hotel_agent import HotelAgent
from app.agents.orchestrator import Orchestrator
from app.inference.confidence import ConfidenceEvaluator
from app.models.budget import BudgetItem
from app.models.travel import TravelerPreference
from app.services.budget_engine import BudgetEngine
from app.services.rag_service import RAGPipeline
from app.tools.executor import ToolExecutor


async def run_evaluation() -> dict:
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluations": {},
    }

    # 1. Evaluate Intent Classification
    intent_tests = [
        ("Find a flight from Chennai to Hyderabad", "flight_search"),
        ("Show me hotels in Paris near Eiffel Tower", "hotel_search"),
        ("Plan a 4-day trip to Hyderabad with ₹20,000 budget", "itinerary_planning"),
        ("What is the baggage limit for IndiGo?", "travel_policy"),
        ("Make my trip cheaper", "budget_optimization"),
    ]
    correct_intents = 0
    for query, expected in intent_tests:
        res = ConfidenceEvaluator.evaluate_intent(query)
        if res.intent == expected:
            correct_intents += 1
    intent_acc = correct_intents / len(intent_tests)
    results["evaluations"]["intent_classification"] = {
        "accuracy": round(intent_acc, 2),
        "total_tested": len(intent_tests),
        "status": "PASS" if intent_acc >= 0.80 else "FAIL",
    }

    # 2. Evaluate Deterministic Budget Arithmetic
    budget = BudgetEngine.build_itemized_budget(
        duration_days=4,
        travelers=1,
        daily_food_per_person=800.0,
        daily_transport_per_person=450.0,
        include_insurance=False,
    )
    food_cat = next((c for c in budget.categories if c.category == "food"), None)
    transport_cat = next((c for c in budget.categories if c.category == "local_transportation"), None)

    math_exact = (
        food_cat is not None
        and food_cat.subtotal == 3200.0
        and transport_cat is not None
        and transport_cat.subtotal == 1800.0
        and budget.grand_total == 5000.0
    )
    results["evaluations"]["budget_arithmetic"] = {
        "deterministic_math_exact": math_exact,
        "calculated_grand_total": budget.grand_total,
        "status": "PASS" if math_exact else "FAIL",
    }

    # 3. Evaluate RAG Retrieval & Relevance
    rag_docs = RAGPipeline.retrieve("IndiGo domestic baggage allowance", limit=2)
    rag_topics = [d.get("topic", "") for d in rag_docs]
    rag_hit = any("IndiGo" in t or "Baggage" in t for t in rag_topics)
    results["evaluations"]["rag_retrieval"] = {
        "hit_found": rag_hit,
        "retrieved_topics": rag_topics,
        "status": "PASS" if rag_hit else "FAIL",
    }

    # 4. Evaluate Recommendation Engine Preference Grounding
    pref = TravelerPreference(dietary_requirements=["vegetarian"], crowd_preference="low_crowds")
    hotel_agent = HotelAgent()
    hotels = await hotel_agent.find_and_rank_hotels(city="Hyderabad", nights=3, preference=pref)
    top_hotel = hotels[0] if hotels else None
    pref_match = top_hotel is not None and (
        "veg" in top_hotel.recommendation_reason.lower() or top_hotel.score > 70.0
    )
    results["evaluations"]["recommendation_ranking"] = {
        "preference_grounded": pref_match,
        "top_pick": top_hotel.name if top_hotel else None,
        "recommendation_reason": top_hotel.recommendation_reason if top_hotel else None,
        "status": "PASS" if pref_match else "FAIL",
    }

    # 5. Evaluate Tool Execution
    executor = ToolExecutor()
    tool_rec = await executor.execute_tool(
        "search_flights",
        {"origin": "Chennai", "destination": "Hyderabad", "travelers": 1},
    )
    tool_success = tool_rec.status == "success" and tool_rec.result.get("count", 0) > 0
    results["evaluations"]["tool_execution"] = {
        "tool_success": tool_success,
        "latency_ms": tool_rec.latency_ms,
        "flight_count": tool_rec.result.get("count", 0) if tool_rec.result else 0,
        "status": "PASS" if tool_success else "FAIL",
    }

    all_passed = all(ev["status"] == "PASS" for ev in results["evaluations"].values())
    results["overall_status"] = "ALL_BENCHMARKS_PASSED" if all_passed else "SOME_FAILED"
    return results


if __name__ == "__main__":
    res = asyncio.run(run_evaluation())
    print(json.dumps(res, indent=2))
