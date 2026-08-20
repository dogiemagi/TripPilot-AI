import pytest
from app.models.budget import PriceMetadata
from app.models.travel import FlightOption, HotelOption, TravelerPreference
from app.services.rag_service import RAGPipeline
from app.services.recommendation_engine import RecommendationEngine


def test_rag_retrieval_and_reranking():
    docs = RAGPipeline.retrieve("IndiGo domestic baggage allowance", limit=2)
    assert len(docs) > 0
    assert any("IndiGo" in d.get("topic", "") or "Baggage" in d.get("topic", "") for d in docs)


def test_flight_recommendation_ranking_and_reasons():
    flights = [
        FlightOption(
            id="fl-cheap",
            airline="SpiceJet",
            flight_number="SG-304",
            origin="Chennai",
            destination="Hyderabad",
            departure_time="18:20",
            arrival_time="19:40",
            duration="1h 20m",
            price=PriceMetadata(amount=3800.0, is_live=False),
        ),
        FlightOption(
            id="fl-indigo",
            airline="IndiGo",
            flight_number="6E-512",
            origin="Chennai",
            destination="Hyderabad",
            departure_time="06:15",
            arrival_time="07:30",
            duration="1h 15m",
            price=PriceMetadata(amount=4200.0, is_live=False),
        ),
    ]

    pref = TravelerPreference(preferred_airlines=["IndiGo"])
    ranked = RecommendationEngine.rank_flights(flights, preference=pref)
    assert len(ranked) == 2
    assert ranked[0].recommendation_reason != ""


def test_hotel_recommendation_dietary_grounding():
    hotels = [
        HotelOption(
            id="ht-veg",
            name="Hotel Midtown Banjara",
            city="Hyderabad",
            neighborhood="Banjara Hills",
            star_rating=3.5,
            user_rating=8.4,
            price_per_night=PriceMetadata(amount=2000.0, is_live=False),
            amenities=["Pure Veg Breakfast"],
            dietary_options=["Pure Veg Restaurant"],
        ),
        HotelOption(
            id="ht-std",
            name="Standard Inn",
            city="Hyderabad",
            neighborhood="City Center",
            star_rating=3.0,
            user_rating=7.5,
            price_per_night=PriceMetadata(amount=2200.0, is_live=False),
        ),
    ]

    pref = TravelerPreference(dietary_requirements=["vegetarian"])
    ranked = RecommendationEngine.rank_hotels(hotels, preference=pref)
    assert ranked[0].id == "ht-veg"
    assert "veg" in ranked[0].recommendation_reason.lower()
