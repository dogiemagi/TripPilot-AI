import pytest
from app.inference.confidence import ConfidenceEvaluator
from app.inference.router import InferenceRouter


def test_intent_detection():
    r1 = ConfidenceEvaluator.evaluate_intent("Find me a cheap flight to Hyderabad")
    assert r1.intent == "flight_search"
    assert r1.confidence >= 0.70

    r2 = ConfidenceEvaluator.evaluate_intent("Looking for 4-star hotels in Paris")
    assert r2.intent == "hotel_search"

    r3 = ConfidenceEvaluator.evaluate_intent("Plan a 4-day trip to Hyderabad under ₹20,000")
    assert r3.intent == "itinerary_planning"
    assert r3.confidence >= 0.90


def test_ambiguity_clarification_trigger():
    # When user gives an underspecified prompt like "Find something cheap for tomorrow"
    res = ConfidenceEvaluator.evaluate_intent("Find something cheap for tomorrow")
    assert res.requires_clarification
    assert res.clarification_prompt is not None
    assert "flight" in res.clarification_prompt.lower() or "hotel" in res.clarification_prompt.lower()


def test_inference_router_model_selection():
    router = InferenceRouter()
    route_img = router.route_request("Check this photo", modality="image")
    assert route_img["task_type"] == "vision_multimodal"

    route_plan = router.route_request("Plan a 4-day trip to Hyderabad")
    assert route_plan["task_type"] in ["reasoning_planning", "fast_chat"]
