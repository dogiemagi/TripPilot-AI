from app.models.budget import (
    BudgetCategory,
    BudgetItem,
    BudgetReductionSuggestion,
    DailyBudget,
    ItemizedBudget,
    PriceMetadata,
)
from app.models.travel import ActivityOption, FlightOption, HotelOption


class BudgetEngine:
    """Deterministic, itemized travel budgeting engine.

    Guarantees exact mathematical calculation without LLM arithmetic errors:
    1. item.total = item.quantity * item.unit_price
    2. category.subtotal = sum(item.total for item in category.items)
    3. grand_total = sum(category.subtotal for category in categories)
    4. daily_budget.total = sum(item.total for item in daily_items)
    """

    @staticmethod
    def calculate_item_total(quantity: int, unit_price: float) -> float:
        return round(float(quantity) * float(unit_price), 2)

    @classmethod
    def build_itemized_budget(
        cls,
        flight: FlightOption | None = None,
        hotel: HotelOption | None = None,
        activities: list[ActivityOption] | None = None,
        duration_days: int = 3,
        travelers: int = 1,
        daily_food_per_person: float = 800.0,
        daily_transport_per_person: float = 450.0,
        include_insurance: bool = True,
        budget_ceiling: float | None = None,
        custom_items: list[BudgetItem] | None = None,
    ) -> ItemizedBudget:
        categories_dict: dict[str, list[BudgetItem]] = {
            "flight": [],
            "hotel": [],
            "food": [],
            "local_transportation": [],
            "activities": [],
            "insurance": [],
            "taxes_fees": [],
            "miscellaneous": [],
        }

        # 1. Flights
        if flight:
            unit_price = flight.price.amount / travelers if travelers > 0 else flight.price.amount
            total = cls.calculate_item_total(travelers, unit_price)
            categories_dict["flight"].append(
                BudgetItem(
                    name=f"Flight ({flight.origin} → {flight.destination}, {flight.airline} {flight.flight_number})",
                    category="flight",
                    quantity=travelers,
                    unit_price=round(unit_price, 2),
                    total=total,
                    day=1,
                    price_metadata=flight.price,
                    notes=f"{flight.cabin_class}, {flight.baggage}",
                )
            )

        # 2. Hotels
        if hotel:
            nights = hotel.nights or max(1, duration_days - 1)
            unit_price = hotel.price_per_night.amount
            total = cls.calculate_item_total(nights, unit_price)
            categories_dict["hotel"].append(
                BudgetItem(
                    name=f"Hotel ({hotel.name}, {hotel.neighborhood})",
                    category="hotel",
                    quantity=nights,
                    unit_price=round(unit_price, 2),
                    total=total,
                    day=1,
                    price_metadata=hotel.price_per_night,
                    notes=f"{nights} nights stay, {hotel.star_rating}★ ({hotel.cancellation_policy})",
                )
            )

        # 3. Food (Daily calculated)
        total_food_units = duration_days * travelers
        total_food = cls.calculate_item_total(total_food_units, daily_food_per_person)
        categories_dict["food"].append(
            BudgetItem(
                name=f"Daily Meals & Dining ({duration_days} days × {travelers} traveler{'s' if travelers > 1 else ''})",
                category="food",
                quantity=total_food_units,
                unit_price=round(daily_food_per_person, 2),
                total=total_food,
                notes="Breakfast, lunch, dinners & local specialties",
            )
        )

        # 4. Local Transportation (Metro, Cabs, Auto-rickshaws)
        total_transport_units = duration_days * travelers
        total_transport = cls.calculate_item_total(total_transport_units, daily_transport_per_person)
        categories_dict["local_transportation"].append(
            BudgetItem(
                name=f"Local City Transit & Cabs ({duration_days} days)",
                category="local_transportation",
                quantity=total_transport_units,
                unit_price=round(daily_transport_per_person, 2),
                total=total_transport,
                notes="Metro rides, airport transfers, city cabs",
            )
        )

        # 5. Activities
        if activities:
            for idx, act in enumerate(activities):
                assigned_day = min(duration_days, (idx % duration_days) + 1)
                unit_p = act.price.amount
                act_total = cls.calculate_item_total(travelers, unit_p)
                categories_dict["activities"].append(
                    BudgetItem(
                        name=f"{act.name} ({act.category})",
                        category="activities",
                        quantity=travelers,
                        unit_price=round(unit_p, 2),
                        total=act_total,
                        day=assigned_day,
                        price_metadata=act.price,
                        notes=f"Crowd: {act.crowd_level.title()}, Rating: {act.rating}★",
                    )
                )

        # 6. Travel Insurance
        if include_insurance:
            insurance_rate = 250.0
            insurance_total = cls.calculate_item_total(travelers, insurance_rate)
            categories_dict["insurance"].append(
                BudgetItem(
                    name="Travel Medical & Baggage Protection",
                    category="insurance",
                    quantity=travelers,
                    unit_price=insurance_rate,
                    total=insurance_total,
                    day=1,
                    notes="Medical coverage, luggage delay, trip cancellation",
                )
            )

        # 7. Custom / Miscellaneous items
        if custom_items:
            for custom in custom_items:
                cat = custom.category if custom.category in categories_dict else "miscellaneous"
                categories_dict[cat].append(custom)

        # Calculate category subtotals and grand total
        categories_list: list[BudgetCategory] = []
        grand_total = 0.0

        for cat_name, items in categories_dict.items():
            if not items:
                continue
            subtotal = round(sum(i.total for i in items), 2)
            categories_list.append(
                BudgetCategory(
                    category=cat_name,
                    items=items,
                    subtotal=subtotal,
                )
            )
            grand_total = round(grand_total + subtotal, 2)

        # Calculate daily breakdown
        daily_breakdown: list[DailyBudget] = []
        for d in range(1, duration_days + 1):
            day_items: list[BudgetItem] = []
            # Pro-rate base daily costs
            day_items.append(
                BudgetItem(
                    name=f"Day {d} Dining Allocation",
                    category="food",
                    quantity=travelers,
                    unit_price=daily_food_per_person,
                    total=cls.calculate_item_total(travelers, daily_food_per_person),
                    day=d,
                )
            )
            day_items.append(
                BudgetItem(
                    name=f"Day {d} Local Transit Allocation",
                    category="local_transportation",
                    quantity=travelers,
                    unit_price=daily_transport_per_person,
                    total=cls.calculate_item_total(travelers, daily_transport_per_person),
                    day=d,
                )
            )
            # Add day 1 upfronts (flight, insurance)
            if d == 1:
                if flight:
                    day_items.extend(categories_dict["flight"])
                if include_insurance:
                    day_items.extend(categories_dict["insurance"])

            # Hotel split per day (if stay on that night)
            if hotel and d < duration_days:
                day_items.append(
                    BudgetItem(
                        name=f"Night {d} Stay ({hotel.name})",
                        category="hotel",
                        quantity=1,
                        unit_price=hotel.price_per_night.amount,
                        total=hotel.price_per_night.amount,
                        day=d,
                    )
                )

            # Activities for this day
            for act_item in categories_dict["activities"]:
                if act_item.day == d:
                    day_items.append(act_item)

            day_total = round(sum(i.total for i in day_items), 2)
            daily_breakdown.append(
                DailyBudget(
                    day=d,
                    items=day_items,
                    total=day_total,
                )
            )

        # Budget Ceiling analysis & Suggestions
        remaining_budget = None
        is_over_budget = False
        overage_amount = 0.0
        reduction_suggestions: list[BudgetReductionSuggestion] = []

        if budget_ceiling is not None and budget_ceiling > 0:
            remaining_budget = round(budget_ceiling - grand_total, 2)
            if grand_total > budget_ceiling:
                is_over_budget = True
                overage_amount = round(grand_total - budget_ceiling, 2)

                # Generate actionable reduction suggestions
                if hotel and hotel.price_per_night.amount > 2500:
                    saving = (hotel.price_per_night.amount - 2000) * (hotel.nights or (duration_days - 1))
                    reduction_suggestions.append(
                        BudgetReductionSuggestion(
                            category="hotel",
                            action="Switch to a 3-star boutique hotel near transit",
                            estimated_saving=round(saving, 2),
                            description="Select Midtown Hotel instead of Luxury/Premium options.",
                        )
                    )
                if flight and flight.price.amount > 4500:
                    saving = flight.price.amount - 3800
                    reduction_suggestions.append(
                        BudgetReductionSuggestion(
                            category="flight",
                            action="Select early morning or late evening flight carrier",
                            estimated_saving=round(saving, 2),
                            description="Fly via SpiceJet or low-cost direct carrier.",
                        )
                    )
                if len(categories_dict["activities"]) > 2:
                    reduction_suggestions.append(
                        BudgetReductionSuggestion(
                            category="activities",
                            action="Focus on free heritage self-guided walks",
                            estimated_saving=600.0,
                            description="Replace paid entry tours with scenic heritage neighborhood walks.",
                        )
                    )

        return ItemizedBudget(
            currency="INR",
            categories=categories_list,
            daily_breakdown=daily_breakdown,
            grand_total=grand_total,
            budget_ceiling=budget_ceiling,
            remaining_budget=remaining_budget,
            is_over_budget=is_over_budget,
            overage_amount=overage_amount,
            reduction_suggestions=reduction_suggestions,
        )
