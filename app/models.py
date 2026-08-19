from typing import Literal

from pydantic import BaseModel, Field


class TravelerProfile(BaseModel):
    travel_style: list[str] = Field(default_factory=list)
    dietary_requirements: list[str] = Field(default_factory=list)
    hotel_preference: str | None = None
    budget_level: Literal["low", "medium", "high"] | None = None


class TravelRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=4000)
    profile: TravelerProfile | None = None
    detected_landmark: str | None = None


class Candidate(BaseModel):
    name: str
    price_score: float = Field(ge=0, le=1)
    location_score: float = Field(ge=0, le=1)
    rating_score: float = Field(ge=0, le=1)
    preference_score: float = Field(ge=0, le=1)
    amenities_score: float = Field(ge=0, le=1)


class RankRequest(BaseModel):
    candidates: list[Candidate] = Field(min_length=1, max_length=20)
