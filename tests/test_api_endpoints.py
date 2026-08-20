import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "total_requests" in response.json()


def test_chat_endpoint_e2e():
    payload = {
        "user_id": "api-test-user-1",
        "text": "I'm going to Hyderabad for 4 days with a ₹20,000 budget. I prefer vegetarian food and less crowded places.",
    }
    response = client.post("/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "itinerary_planning"
    assert "Hyderabad" in data["answer"]
    assert data["budget"] is not None
    assert data["budget"]["grand_total"] > 0
    assert len(data["flight_recommendations"]) > 0
    assert len(data["hotel_recommendations"]) > 0


def test_search_flights_endpoint():
    response = client.post(
        "/v1/search/flights",
        json={"origin": "Chennai", "destination": "Hyderabad", "travelers": 1},
    )
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_search_hotels_endpoint():
    response = client.post(
        "/v1/search/hotels",
        json={"city": "Hyderabad", "nights": 3, "guests": 1},
    )
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_pdf_generation_endpoint():
    payload = {
        "title": "Hyderabad 4-Day Plan",
        "answer": "Test brief for Hyderabad.",
        "context": ["IndiGo Baggage: 15kg included"],
    }
    response = client.post("/v1/plan/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 100
