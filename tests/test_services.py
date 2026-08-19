from app.models import Candidate
from app.services import detect_intent, score_candidate


def test_detect_hotel_intent():
    assert detect_intent("Find a cheap hotel in Paris")[0] == "hotel_search"


def test_decision_score():
    candidate = Candidate(name="Central Stay", price_score=.9, location_score=.9, rating_score=.8, preference_score=.8, amenities_score=.7)
    assert score_candidate(candidate)["score"] == 85.0
