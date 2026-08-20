from datetime import datetime, timezone

from app.models.budget import PriceMetadata
from app.models.travel import ActivityOption
from .base import ActivityProvider


MOCK_ACTIVITY_CATALOG = [
    # Hyderabad Activities & Dining
    {
        "id": "act-hyd-001",
        "name": "Golconda Fort Sound & Light Show",
        "city": "Hyderabad",
        "category": "Heritage Attraction",
        "description": "Historic acoustic fort architecture and evening light show.",
        "estimated_duration_hours": 3.0,
        "ticket_price": 200.0,
        "crowd_level": "moderate",
        "dietary_tags": [],
        "best_time": "Late Afternoon",
        "rating": 4.6,
        "distance_km": 8.0,
    },
    {
        "id": "act-hyd-002",
        "name": "Chutneys Pure Veg Dining",
        "city": "Hyderabad",
        "category": "Culinary Experience",
        "description": "Famous 7-chutney Guntur Idli and South Indian vegetarian thali.",
        "estimated_duration_hours": 1.5,
        "ticket_price": 400.0,
        "crowd_level": "moderate",
        "dietary_tags": ["pure_vegetarian", "vegan_friendly", "south_indian"],
        "best_time": "Morning/Afternoon",
        "rating": 4.7,
        "distance_km": 3.2,
    },
    {
        "id": "act-hyd-003",
        "name": "Qutb Shahi Tombs Heritage Walk",
        "city": "Hyderabad",
        "category": "Heritage Attraction",
        "description": "Magnificent domed mausoleums set in peaceful landscaped gardens.",
        "estimated_duration_hours": 2.0,
        "ticket_price": 100.0,
        "crowd_level": "low",
        "dietary_tags": [],
        "best_time": "Early Morning",
        "rating": 4.8,
        "distance_km": 6.5,
    },
    {
        "id": "act-hyd-004",
        "name": "Charminar & Laad Bazaar Evening Walk",
        "city": "Hyderabad",
        "category": "Culture & Markets",
        "description": "Iconic 1591 monument, lacquer bangles, and Irani Chai bakeries.",
        "estimated_duration_hours": 2.5,
        "ticket_price": 50.0,
        "crowd_level": "high",
        "dietary_tags": ["tea_snacks", "vegetarian_sweets"],
        "best_time": "Evening",
        "rating": 4.5,
        "distance_km": 4.0,
    },
    {
        "id": "act-hyd-005",
        "name": "Subbayya Gari Pure Veg Royal Bhojanam",
        "city": "Hyderabad",
        "category": "Culinary Experience",
        "description": "Traditional Andhra banana leaf vegetarian feast served with warm ghee.",
        "estimated_duration_hours": 1.5,
        "ticket_price": 450.0,
        "crowd_level": "moderate",
        "dietary_tags": ["pure_vegetarian", "andhra_meals"],
        "best_time": "Lunch",
        "rating": 4.7,
        "distance_km": 5.0,
    },
    # Paris Activities
    {
        "id": "act-par-001",
        "name": "Louvre Museum Priority Entry",
        "city": "Paris",
        "category": "Museum",
        "description": "Mona Lisa, Venus de Milo, and world-class classical art galleries.",
        "estimated_duration_hours": 3.5,
        "ticket_price": 1900.0,
        "crowd_level": "high",
        "dietary_tags": [],
        "best_time": "Morning",
        "rating": 4.7,
        "distance_km": 1.5,
    },
    {
        "id": "act-par-002",
        "name": "Montmartre & Sacré-Cœur Walking Tour",
        "city": "Paris",
        "category": "Sightseeing",
        "description": "Bohemian artist quarter, panoramic city views, and quiet alleys.",
        "estimated_duration_hours": 2.5,
        "ticket_price": 600.0,
        "crowd_level": "moderate",
        "dietary_tags": ["bistro_vegetarian"],
        "best_time": "Afternoon",
        "rating": 4.6,
        "distance_km": 4.0,
    },
    # Goa Activities
    {
        "id": "act-goa-001",
        "name": "Fontainhas Latin Quarter Heritage Walk",
        "city": "Goa",
        "category": "Heritage Walk",
        "description": "Colorful Portuguese-era architecture, heritage bakeries, and art galleries.",
        "estimated_duration_hours": 2.0,
        "ticket_price": 300.0,
        "crowd_level": "low",
        "dietary_tags": ["vegetarian_cafes"],
        "best_time": "Morning",
        "rating": 4.8,
        "distance_km": 2.0,
    },
]


class MockActivityProvider(ActivityProvider):
    async def search_activities(
        self,
        city: str,
        category: str | None = None,
        dietary_tags: list[str] | None = None,
        crowd_preference: str | None = None,
    ) -> list[ActivityOption]:
        norm_city = city.strip().lower()
        matched = [a for a in MOCK_ACTIVITY_CATALOG if norm_city in a["city"].lower()]

        if not matched:
            matched = [
                {
                    "id": f"act-{norm_city[:3]}-sight1",
                    "name": f"Historic Landmarks Tour {city.title()}",
                    "city": city.title(),
                    "category": "Sightseeing",
                    "description": f"Guided orientation of top cultural landmarks across {city.title()}.",
                    "estimated_duration_hours": 3.0,
                    "ticket_price": 400.0,
                    "crowd_level": "moderate",
                    "dietary_tags": [],
                    "best_time": "Morning",
                    "rating": 4.5,
                    "distance_km": 2.5,
                },
                {
                    "id": f"act-{norm_city[:3]}-food1",
                    "name": f"Local Cuisine & Vegetarian Tasting {city.title()}",
                    "city": city.title(),
                    "category": "Culinary Experience",
                    "description": f"Curated vegetarian food walk sampling authentic local dishes in {city.title()}.",
                    "estimated_duration_hours": 2.0,
                    "ticket_price": 500.0,
                    "crowd_level": "low",
                    "dietary_tags": ["pure_vegetarian", "local_delicacies"],
                    "best_time": "Lunch",
                    "rating": 4.7,
                    "distance_km": 1.5,
                },
            ]

        results = []
        for a in matched:
            # Filter crowd if requested
            if crowd_preference == "low_crowds" and a["crowd_level"] == "high":
                continue

            # Prioritize matching dietary tags if present
            results.append(
                ActivityOption(
                    id=a["id"],
                    name=a["name"],
                    city=a["city"],
                    category=a["category"],
                    description=a["description"],
                    estimated_duration_hours=a["estimated_duration_hours"],
                    price=PriceMetadata(
                        amount=a["ticket_price"],
                        currency="INR",
                        source="mock_activity_provider",
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        is_live=False,
                        price_type="mock",
                    ),
                    crowd_level=a["crowd_level"],
                    dietary_tags=a["dietary_tags"],
                    best_time=a["best_time"],
                    rating=a["rating"],
                    distance_km=a["distance_km"],
                )
            )
        return results


class ActivityProviderAggregator(ActivityProvider):
    def __init__(self) -> None:
        self.mock_provider = MockActivityProvider()

    async def search_activities(
        self,
        city: str,
        category: str | None = None,
        dietary_tags: list[str] | None = None,
        crowd_preference: str | None = None,
    ) -> list[ActivityOption]:
        return await self.mock_provider.search_activities(
            city, category, dietary_tags, crowd_preference
        )
