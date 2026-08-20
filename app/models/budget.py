from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class PriceMetadata(BaseModel):
    amount: float = Field(ge=0, description="Numerical price amount")
    currency: str = Field(default="INR", description="ISO currency code, e.g. INR, USD, EUR")
    source: str = Field(default="mock_provider", description="Provider or calculation source")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when price was fetched"
    )
    is_live: bool = Field(default=False, description="Whether price is directly from live API")
    price_type: Literal["live", "cached", "estimated", "mock"] = Field(
        default="mock",
        description="Data freshness and source type"
    )


class BudgetItem(BaseModel):
    name: str = Field(min_length=1)
    category: Literal[
        "flight", "hotel", "food", "local_transportation",
        "activities", "insurance", "taxes_fees", "miscellaneous"
    ]
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)
    total: float = Field(ge=0)
    day: int | None = Field(default=None, ge=1)
    price_metadata: PriceMetadata | None = None
    notes: str | None = None


class BudgetCategory(BaseModel):
    category: str
    items: list[BudgetItem] = Field(default_factory=list)
    subtotal: float = Field(default=0.0, ge=0)


class DailyBudget(BaseModel):
    day: int = Field(ge=1)
    date: str | None = None
    items: list[BudgetItem] = Field(default_factory=list)
    total: float = Field(default=0.0, ge=0)


class BudgetReductionSuggestion(BaseModel):
    category: str
    action: str
    estimated_saving: float = Field(ge=0)
    description: str
    alternative_option_id: str | None = None


class ItemizedBudget(BaseModel):
    currency: str = "INR"
    categories: list[BudgetCategory] = Field(default_factory=list)
    daily_breakdown: list[DailyBudget] = Field(default_factory=list)
    grand_total: float = Field(default=0.0, ge=0)
    budget_ceiling: float | None = None
    remaining_budget: float | None = None
    is_over_budget: bool = False
    overage_amount: float = 0.0
    reduction_suggestions: list[BudgetReductionSuggestion] = Field(default_factory=list)
