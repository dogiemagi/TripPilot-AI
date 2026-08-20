from typing import Any
from app.models.travel import (
    ActivityOption,
    FlightOption,
    HotelOption,
    TravelerPreference,
)


class ItineraryAgent:
    @staticmethod
    def build_schedule(
        destination: str,
        duration_days: int,
        flight: FlightOption | None,
        hotel: HotelOption | None,
        activities: list[ActivityOption],
        preference: TravelerPreference | None = None,
    ) -> list[dict[str, Any]]:
        days: list[dict[str, Any]] = []

        is_veg = preference and "vegetarian" in [d.lower() for d in preference.dietary_requirements]
        is_low_crowd = preference and preference.crowd_preference == "low_crowds"

        for d in range(1, duration_days + 1):
            day_plan: dict[str, Any] = {
                "day": d,
                "title": f"Day {d} in {destination}",
                "morning": "",
                "afternoon": "",
                "evening": "",
                "highlights": [],
            }

            if d == 1:
                flight_str = f"Arrive via {flight.airline} ({flight.flight_number}) at {flight.arrival_time}. " if flight else "Arrive at destination. "
                hotel_str = f"Check-in at {hotel.name} ({hotel.neighborhood}). " if hotel else "Drop luggage and settle in. "
                day_plan["title"] = f"Day 1: Arrival & Orientation in {destination}"
                day_plan["morning"] = flight_str + hotel_str
                act_day1 = [a for a in activities if "walk" in a.name.lower() or "lunch" in a.best_time.lower() or "afternoon" in a.best_time.lower()]
                act = act_day1[0] if act_day1 else (activities[0] if activities else None)
                if act:
                    day_plan["afternoon"] = f"Visit {act.name}: {act.description} (Crowd: {act.crowd_level.title()})."
                    day_plan["highlights"].append(act.name)
                else:
                    day_plan["afternoon"] = "Orientation neighborhood stroll and café break."

                dining_tip = "Enjoy a traditional Pure Vegetarian Thali at a nearby heritage restaurant." if is_veg else "Local specialty dinner."
                day_plan["evening"] = f"Relaxed evening dinner: {dining_tip} Settle in early to recharge."

            elif d == 2:
                day_plan["title"] = f"Day 2: Cultural Anchor & Heritage in {destination}"
                morning_acts = [a for a in activities if "morning" in a.best_time.lower() or a.crowd_level == "low"]
                act_m = morning_acts[0] if morning_acts else (activities[1] if len(activities) > 1 else None)
                if act_m:
                    crowd_note = " (Early entry avoids peak crowds)" if is_low_crowd else ""
                    day_plan["morning"] = f"Anchor Sight: Explore {act_m.name}{crowd_note}. {act_m.description}"
                    day_plan["highlights"].append(act_m.name)
                else:
                    day_plan["morning"] = "Explore prime historical landmarks and architectural wonders."

                food_acts = [a for a in activities if "dining" in a.category.lower() or "culinary" in a.category.lower()]
                food_act = food_acts[0] if food_acts else None
                if food_act:
                    day_plan["afternoon"] = f"Culinary highlight: {food_act.name} — {food_act.description}"
                    day_plan["highlights"].append(food_act.name)
                else:
                    day_plan["afternoon"] = "Curated regional lunch followed by a museum or artisan quarter visit."

                day_plan["evening"] = "Sunset viewpoints and illuminated city landmarks stroll."

            elif d == 3:
                day_plan["title"] = f"Day 3: Hidden Gems & Local Flavors in {destination}"
                other_acts = [a for a in activities if a.name not in day_plan.get("highlights", [])]
                act_3 = other_acts[0] if other_acts else None
                if act_3:
                    day_plan["morning"] = f"Explore {act_3.name}: {act_3.description}"
                    day_plan["highlights"].append(act_3.name)
                else:
                    day_plan["morning"] = "Morning artisan bazaar exploration and heritage photography."
                day_plan["afternoon"] = "Leisurely lunch break, sweet shops, and craft souvenirs."
                day_plan["evening"] = "Scenic sunset walk and special farewell dinner."

            else:
                day_plan["title"] = f"Day {d}: Flexible Leisure & Departure"
                day_plan["morning"] = "Leisurely breakfast, packing, and final market visits."
                day_plan["afternoon"] = "Souvenir shopping and airport transfer."
                day_plan["evening"] = "Departure return journey."

            days.append(day_plan)

        return days
