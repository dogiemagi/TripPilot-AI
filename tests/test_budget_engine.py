import pytest
from app.models.budget import BudgetItem, PriceMetadata
from app.models.travel import ActivityOption, FlightOption, HotelOption
from app.services.budget_engine import BudgetEngine


def test_deterministic_item_arithmetic():
    assert BudgetEngine.calculate_item_total(1, 4200.0) == 4200.0
    assert BudgetEngine.calculate_item_total(4, 2500.0) == 10000.0
    assert BudgetEngine.calculate_item_total(3, 800.0) == 2400.0


def test_full_itemized_budget_calculation():
    flight = FlightOption(
        id="fl-1",
        airline="IndiGo",
        flight_number="6E-512",
        origin="Chennai",
        destination="Hyderabad",
        departure_time="06:15",
        arrival_time="07:30",
        duration="1h 15m",
        price=PriceMetadata(amount=4200.0, currency="INR", source="mock", is_live=False),
    )
    hotel = HotelOption(
        id="ht-1",
        name="Hotel Midtown",
        city="Hyderabad",
        neighborhood="Banjara Hills",
        star_rating=3.5,
        user_rating=8.4,
        nights=3,
        price_per_night=PriceMetadata(amount=2500.0, currency="INR", source="mock", is_live=False),
    )
    activity = ActivityOption(
        id="act-1",
        name="Golconda Fort",
        city="Hyderabad",
        price=PriceMetadata(amount=200.0, currency="INR", source="mock", is_live=False),
    )

    budget = BudgetEngine.build_itemized_budget(
        flight=flight,
        hotel=hotel,
        activities=[activity],
        duration_days=4,
        travelers=1,
        daily_food_per_person=800.0,
        daily_transport_per_person=450.0,
        include_insurance=True,
        budget_ceiling=20000.0,
    )

    # Flight: 4200
    # Hotel: 3 nights * 2500 = 7500
    # Food: 4 days * 800 = 3200
    # Transport: 4 days * 450 = 1800
    # Activity: 200
    # Insurance: 250
    # Grand Total = 4200 + 7500 + 3200 + 1800 + 200 + 250 = 17150
    assert budget.grand_total == 17150.0
    assert budget.remaining_budget == 2850.0
    assert not budget.is_over_budget
    assert budget.overage_amount == 0.0

    # Ensure sum of category subtotals equals grand total exactly
    cat_sum = sum(c.subtotal for c in budget.categories)
    assert round(cat_sum, 2) == budget.grand_total


def test_over_budget_detection_and_suggestions():
    # High-cost luxury stay causing over-budget
    hotel_luxury = HotelOption(
        id="ht-lux",
        name="ITC Luxury",
        city="Hyderabad",
        neighborhood="Madhapur",
        star_rating=5.0,
        user_rating=9.4,
        nights=3,
        price_per_night=PriceMetadata(amount=7500.0, currency="INR", source="mock", is_live=False),
    )
    budget = BudgetEngine.build_itemized_budget(
        hotel=hotel_luxury,
        duration_days=4,
        travelers=1,
        budget_ceiling=20000.0,
    )

    # Hotel: 3 * 7500 = 22500, already over 20,000 ceiling!
    assert budget.is_over_budget
    assert budget.overage_amount > 0.0
    assert len(budget.reduction_suggestions) > 0
    assert any("hotel" in s.category.lower() for s in budget.reduction_suggestions)
