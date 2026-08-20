from datetime import datetime, timezone

from app.models.budget import PriceMetadata
from app.models.travel import HotelOption
from .base import HotelProvider


MOCK_HOTEL_CATALOG = [
    # Hyderabad Hotels
    {
        "id": "ht-hyd-001",
        "name": "Hotel Midtown Banjara",
        "city": "Hyderabad",
        "neighborhood": "Banjara Hills",
        "star_rating": 3.5,
        "user_rating": 8.4,
        "price_per_night": 2000.0,
        "amenities": ["Free Wi-Fi", "Pure Veg Breakfast", "AC", "Airport Shuttle"],
        "dietary_options": ["Pure Veg Restaurant", "South Indian Breakfast"],
        "distance_to_center_km": 2.1,
        "cancellation_policy": "Free cancellation up to 24 hours before check-in",
    },
    {
        "id": "ht-hyd-002",
        "name": "Lemon Tree Premier Hitec City",
        "city": "Hyderabad",
        "neighborhood": "Hitec City",
        "star_rating": 4.0,
        "user_rating": 8.8,
        "price_per_night": 2500.0,
        "amenities": ["Pool", "Fitness Center", "High-speed Wi-Fi", "Multi-cuisine Dining"],
        "dietary_options": ["Vegetarian buffet section", "Jain food on request"],
        "distance_to_center_km": 5.4,
        "cancellation_policy": "Free cancellation up to 48 hours before check-in",
    },
    {
        "id": "ht-hyd-003",
        "name": "ITC Kohenur Luxury Collection",
        "city": "Hyderabad",
        "neighborhood": "Madhapur",
        "star_rating": 5.0,
        "user_rating": 9.4,
        "price_per_night": 7500.0,
        "amenities": ["Luxury Spa", "Infinity Pool", "Butler Service", "Valet"],
        "dietary_options": ["Royal Hyderabadi Vegetarian Thali", "Organic Dining"],
        "distance_to_center_km": 6.2,
        "cancellation_policy": "Non-refundable within 3 days",
    },
    # Paris Hotels
    {
        "id": "ht-par-001",
        "name": "Hotel Eiffel Rive Gauche",
        "city": "Paris",
        "neighborhood": "7th Arrondissement",
        "star_rating": 3.5,
        "user_rating": 8.6,
        "price_per_night": 11500.0,
        "amenities": ["Eiffel View", "Breakfast Lounge", "Free Wi-Fi"],
        "dietary_options": ["Vegetarian continental breakfast"],
        "distance_to_center_km": 0.6,
        "cancellation_policy": "Free cancellation up to 48 hours before arrival",
    },
    # Dubai Hotels
    {
        "id": "ht-dxb-001",
        "name": "Rove Downtown Dubai",
        "city": "Dubai",
        "neighborhood": "Downtown",
        "star_rating": 4.0,
        "user_rating": 8.9,
        "price_per_night": 8200.0,
        "amenities": ["Burj Khalifa View", "Pool", "24h Gym", "Metro Link"],
        "dietary_options": ["Vegetarian & Halal friendly"],
        "distance_to_center_km": 1.2,
        "cancellation_policy": "Free cancellation up to 24 hours before check-in",
    },
    # Goa Hotels
    {
        "id": "ht-goa-001",
        "name": "Heritage Village Resort & Spa",
        "city": "Goa",
        "neighborhood": "Arossim Beach (South Goa)",
        "star_rating": 4.0,
        "user_rating": 8.7,
        "price_per_night": 4200.0,
        "amenities": ["Beach Access", "Ayurvedic Spa", "Pool", "Gardens"],
        "dietary_options": ["Coastal Vegetarian Delicacies", "Goan Breakfast"],
        "distance_to_center_km": 0.4,
        "cancellation_policy": "Free cancellation up to 7 days before check-in",
    },
]


class MockHotelProvider(HotelProvider):
    async def search_hotels(
        self,
        city: str,
        nights: int = 1,
        guests: int = 1,
        min_rating: float = 0.0,
        max_price_per_night: float | None = None,
        dietary_preference: str | None = None,
    ) -> list[HotelOption]:
        norm_city = city.strip().lower()
        matched = [h for h in MOCK_HOTEL_CATALOG if norm_city in h["city"].lower()]

        if not matched:
            matched = [
                {
                    "id": f"ht-{norm_city[:3]}-std1",
                    "name": f"Grand Central Hotel {city.title()}",
                    "city": city.title(),
                    "neighborhood": "City Center",
                    "star_rating": 3.5,
                    "user_rating": 8.2,
                    "price_per_night": 2200.0,
                    "amenities": ["Free Wi-Fi", "Breakfast", "AC"],
                    "dietary_options": ["Vegetarian Friendly"],
                    "distance_to_center_km": 1.0,
                    "cancellation_policy": "Free cancellation 24h prior",
                },
                {
                    "id": f"ht-{norm_city[:3]}-prem1",
                    "name": f"Royal Palace Suites {city.title()}",
                    "city": city.title(),
                    "neighborhood": "Heritage District",
                    "star_rating": 4.5,
                    "user_rating": 9.0,
                    "price_per_night": 4500.0,
                    "amenities": ["Spa", "Pool", "Concierge"],
                    "dietary_options": ["Multi-cuisine Vegetarian"],
                    "distance_to_center_km": 2.5,
                    "cancellation_policy": "Free cancellation 48h prior",
                },
            ]

        results = []
        for h in matched:
            if h["user_rating"] < min_rating:
                continue
            if max_price_per_night and h["price_per_night"] > max_price_per_night:
                continue

            rate = h["price_per_night"]
            total_amt = rate * nights

            results.append(
                HotelOption(
                    id=h["id"],
                    name=h["name"],
                    city=h["city"],
                    neighborhood=h["neighborhood"],
                    star_rating=h["star_rating"],
                    user_rating=h["user_rating"],
                    price_per_night=PriceMetadata(
                        amount=rate,
                        currency="INR",
                        source="mock_hotel_provider",
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        is_live=False,
                        price_type="mock",
                    ),
                    nights=nights,
                    total_price=PriceMetadata(
                        amount=total_amt,
                        currency="INR",
                        source="mock_hotel_provider",
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        is_live=False,
                        price_type="mock",
                    ),
                    amenities=h["amenities"],
                    dietary_options=h["dietary_options"],
                    distance_to_center_km=h["distance_to_center_km"],
                    cancellation_policy=h["cancellation_policy"],
                )
            )
        return results


class HotelProviderAggregator(HotelProvider):
    def __init__(self) -> None:
        self.mock_provider = MockHotelProvider()

    async def search_hotels(
        self,
        city: str,
        nights: int = 1,
        guests: int = 1,
        min_rating: float = 0.0,
        max_price_per_night: float | None = None,
        dietary_preference: str | None = None,
    ) -> list[HotelOption]:
        return await self.mock_provider.search_hotels(
            city, nights, guests, min_rating, max_price_per_night, dietary_preference
        )
