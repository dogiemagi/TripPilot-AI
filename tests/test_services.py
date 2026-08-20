from app.models import Candidate
from app.services import detect_intent, score_candidate


def test_detect_hotel_intent():
    assert detect_intent("Find a cheap hotel in Paris")[0] == "hotel_search"


def test_decision_score():
    candidate = Candidate(name="Central Stay", price_score=.9, location_score=.9, rating_score=.8, preference_score=.8, amenities_score=.7)
    # .9*.30 + .9*.25 + .8*.20 + .8*.15 + .7*.10 = 0.27 + 0.225 + 0.16 + 0.12 + 0.07 = 0.845 * 100 = 84.5
    assert score_candidate(candidate)["score"] == 84.5
