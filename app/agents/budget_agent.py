from app.models.budget import ItemizedBudget
from app.models.travel import ActivityOption, FlightOption, HotelOption
from app.services.budget_engine import BudgetEngine


class BudgetAgent:
    @staticmethod
    def calculate_trip_budget(
        flight: FlightOption | None = None,
        hotel: HotelOption | None = None,
        activities: list[ActivityOption] | None = None,
        duration_days: int = 3,
        travelers: int = 1,
        budget_ceiling: float | None = None,
    ) -> ItemizedBudget:
        return BudgetEngine.build_itemized_budget(
            flight=flight,
            hotel=hotel,
            activities=activities,
            duration_days=duration_days,
            travelers=travelers,
            budget_ceiling=budget_ceiling,
        )
