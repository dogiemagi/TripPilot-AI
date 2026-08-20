from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from .budget import PriceMetadata


class TravelerPreference(BaseModel):
    dietary_requirements: list[str] = Field(default_factory=list, description="e.g. ['vegetarian', 'vegan', 'halal']")
    crowd_preference: Literal["low_crowds", "moderate", "any"] = Field(default="moderate")
    preferred_airlines: list[str] = Field(default_factory=list)
    hotel_tier: Literal["budget", "midscale", "luxury", "boutique"] | None = None
    budget_range: tuple[float, float] | None = None
    activity_preferences: list[str] = Field(default_factory=list, description="e.g. ['heritage', 'nature', 'food']")
    seat_preference: Literal["window", "aisle", "extra_legroom", "any"] = "any"


class FlightOption(BaseModel):
    id: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: int = 0
    price: PriceMetadata
    cabin_class: str = "Economy"
    baggage: str = "15kg check-in, 7kg cabin"
    score: float = 0.0
    recommendation_reason: str = ""


class HotelOption(BaseModel):
    id: str
    name: str
    city: str
    neighborhood: str
    star_rating: float = Field(ge=1, le=5)
    user_rating: float = Field(ge=0, le=10)
    price_per_night: PriceMetadata
    nights: int = 1
    total_price: PriceMetadata | None = None
    amenities: list[str] = Field(default_factory=list)
    dietary_options: list[str] = Field(default_factory=list, description="e.g. ['Pure Veg Restaurant', 'Breakfast Included']")
    distance_to_center_km: float = 1.0
    cancellation_policy: str = "Free cancellation up to 24h before check-in"
    score: float = 0.0
    recommendation_reason: str = ""


class ActivityOption(BaseModel):
    id: str
    name: str
    city: str
    category: str = "Attraction"
    description: str = ""
    estimated_duration_hours: float = 2.0
    price: PriceMetadata
    crowd_level: Literal["low", "moderate", "high"] = "moderate"
    dietary_tags: list[str] = Field(default_factory=list, description="e.g. ['pure_vegetarian', 'street_food']")
    best_time: str = "Morning"
    rating: float = 4.5
    distance_km: float = 2.0
    score: float = 0.0
    recommendation_reason: str = ""


class CartItem(BaseModel):
    id: str
    type: Literal["flight", "hotel", "activity", "insurance", "custom"]
    item_id: str
    name: str
    quantity: int = 1
    unit_price: float
    total_price: float
    currency: str = "INR"
    details: dict = Field(default_factory=dict)
    added_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TripState(BaseModel):
    trip_id: str
    user_id: str
    title: str = "Untitled Trip"
    destination: str
    origin: str = "Chennai"
    start_date: str | None = None
    duration_days: int = 3
    travelers: int = 1
    budget_ceiling: float | None = None
    selected_flight: FlightOption | None = None
    selected_hotel: HotelOption | None = None
    selected_activities: list[ActivityOption] = Field(default_factory=list)
    cart_items: list[CartItem] = Field(default_factory=list)
    status: Literal["planning", "customizing", "review", "booking_ready"] = "planning"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
