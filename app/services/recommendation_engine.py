from app.models.travel import (
    ActivityOption,
    FlightOption,
    HotelOption,
    TravelerPreference,
)


class RecommendationEngine:
    DEFAULT_WEIGHTS = {
        "price": 0.30,
        "preference": 0.25,
        "rating": 0.20,
        "location": 0.15,
        "duration": 0.10,
    }

    @classmethod
    def rank_flights(
        cls,
        flights: list[FlightOption],
        preference: TravelerPreference | None = None,
        budget_limit: float | None = None,
        weights: dict[str, float] | None = None,
    ) -> list[FlightOption]:
        if not flights:
            return []
        w = weights or cls.DEFAULT_WEIGHTS
        min_price = min(f.price.amount for f in flights)
        max_price = max(f.price.amount for f in flights) or (min_price + 1.0)

        scored: list[tuple[float, FlightOption, str]] = []
        for fl in flights:
            # 1. Price score (inverse linear)
            price_score = 1.0 - ((fl.price.amount - min_price) / (max_price - min_price)) if max_price > min_price else 1.0

            # 2. Preference score (airline match, non-stop)
            pref_score = 0.5
            pref_reasons = []
            if preference and preference.preferred_airlines:
                if any(pref_air.lower() in fl.airline.lower() for pref_air in preference.preferred_airlines):
                    pref_score += 0.4
                    pref_reasons.append(f"matches preferred airline ({fl.airline})")
            if fl.stops == 0:
                pref_score += 0.1
                pref_reasons.append("direct flight with zero layovers")

            # 3. Rating / Reliability score
            rating_score = 0.9 if "IndiGo" in fl.airline or "Air France" in fl.airline else 0.8

            # 4. Duration score
            duration_score = 1.0 if "1h" in fl.duration or "2h" in fl.duration else 0.7

            total_score = (
                (price_score * w.get("price", 0.30))
                + (min(1.0, pref_score) * w.get("preference", 0.25))
                + (rating_score * w.get("rating", 0.20))
                + (duration_score * w.get("duration", 0.10))
                + (0.8 * w.get("location", 0.15))
            )

            # Build grounded explanation
            price_delta = fl.price.amount - min_price
            if price_delta == 0:
                reason = f"Best value direct flight at ₹{fl.price.amount:,.0f} ({fl.duration}, {fl.airline})"
            else:
                extra_str = f"₹{price_delta:,.0f} above cheapest"
                reasons_str = ", ".join(pref_reasons) if pref_reasons else f"prime timing ({fl.departure_time})"
                reason = f"Recommended: {reasons_str}, only {extra_str}"

            fl.score = round(total_score * 100, 1)
            fl.recommendation_reason = reason
            scored.append((total_score, fl, reason))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored]

    @classmethod
    def rank_hotels(
        cls,
        hotels: list[HotelOption],
        preference: TravelerPreference | None = None,
        budget_limit: float | None = None,
        weights: dict[str, float] | None = None,
    ) -> list[HotelOption]:
        if not hotels:
            return []
        w = weights or cls.DEFAULT_WEIGHTS
        min_rate = min(h.price_per_night.amount for h in hotels)
        max_rate = max(h.price_per_night.amount for h in hotels) or (min_rate + 1.0)

        scored: list[tuple[float, HotelOption]] = []
        for h in hotels:
            # 1. Price score
            price_score = 1.0 - ((h.price_per_night.amount - min_rate) / (max_rate - min_rate)) if max_rate > min_rate else 1.0

            # 2. Preference score (Dietary & Amenities)
            pref_score = 0.5
            reasons = []
            if preference and "vegetarian" in [d.lower() for d in preference.dietary_requirements]:
                if any("veg" in opt.lower() for opt in h.dietary_options) or any("veg" in am.lower() for am in h.amenities):
                    pref_score += 0.4
                    reasons.append("has dedicated pure vegetarian dining")
            if h.distance_to_center_km <= 3.0:
                reasons.append(f"close to central hub ({h.distance_to_center_km} km)")

            # 3. Rating score (normalized 0-10 -> 0-1)
            rating_score = h.user_rating / 10.0

            # 4. Location score (distance penalty)
            loc_score = max(0.2, 1.0 - (h.distance_to_center_km / 10.0))

            total_score = (
                (price_score * w.get("price", 0.30))
                + (min(1.0, pref_score) * w.get("preference", 0.25))
                + (rating_score * w.get("rating", 0.20))
                + (loc_score * w.get("location", 0.15))
                + (0.85 * w.get("duration", 0.10))
            )

            # Natural language reason
            diet_note = " · " + reasons[0] if reasons else ""
            h.score = round(total_score * 100, 1)
            h.recommendation_reason = (
                f"Rated {h.user_rating}/10 ({h.star_rating}★) at ₹{h.price_per_night.amount:,.0f}/night{diet_note}"
            )
            scored.append((total_score, h))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored]

    @classmethod
    def rank_activities(
        cls,
        activities: list[ActivityOption],
        preference: TravelerPreference | None = None,
    ) -> list[ActivityOption]:
        if not activities:
            return []

        for act in activities:
            score = 0.6
            reasons = []
            if preference:
                if preference.crowd_preference == "low_crowds":
                    if act.crowd_level == "low":
                        score += 0.3
                        reasons.append("low-crowd peaceful environment")
                    elif act.crowd_level == "moderate":
                        score += 0.15
                if "vegetarian" in [d.lower() for d in preference.dietary_requirements]:
                    if "pure_vegetarian" in act.dietary_tags:
                        score += 0.35
                        reasons.append("authentic pure vegetarian specialties")

            score += (act.rating / 5.0) * 0.2
            act.score = round(min(1.0, score) * 100, 1)
            act.recommendation_reason = (
                f"{act.category} ({act.best_time}) · {', '.join(reasons) if reasons else 'Top rated attraction'}"
            )

        activities.sort(key=lambda a: a.score, reverse=True)
        return activities
