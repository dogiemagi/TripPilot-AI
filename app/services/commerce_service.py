import uuid
from typing import Literal

from app.database import get_db_connection
from app.models.budget import BudgetItem, ItemizedBudget
from app.models.travel import (
    ActivityOption,
    CartItem,
    FlightOption,
    HotelOption,
    TripState,
)
from app.services.budget_engine import BudgetEngine
from app.services.context_manager import ContextManager


class CommerceService:
    @staticmethod
    def add_to_cart(
        trip_id: str,
        item_type: Literal["flight", "hotel", "activity", "insurance", "custom"],
        item_id: str,
        name: str,
        unit_price: float,
        quantity: int = 1,
        currency: str = "INR",
        details: dict | None = None,
    ) -> CartItem:
        total = round(float(unit_price) * float(quantity), 2)
        cart_item_id = f"cart-{uuid.uuid4().hex[:8]}"
        cart_item = CartItem(
            id=cart_item_id,
            type=item_type,
            item_id=item_id,
            name=name,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total,
            currency=currency,
            details=details or {},
        )

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO cart_items (id, trip_id, type, item_id, name, quantity, unit_price, total_price, currency, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cart_item.id,
                    trip_id,
                    cart_item.type,
                    cart_item.item_id,
                    cart_item.name,
                    cart_item.quantity,
                    cart_item.unit_price,
                    cart_item.total_price,
                    cart_item.currency,
                    cart_item.model_dump_json(),
                ),
            )
        return cart_item

    @staticmethod
    def get_cart_items(trip_id: str) -> list[CartItem]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT details_json FROM cart_items WHERE trip_id = ? ORDER BY created_at ASC",
                (trip_id,),
            ).fetchall()
            items = []
            for r in rows:
                try:
                    items.append(CartItem.model_validate_json(r["details_json"]))
                except Exception:
                    pass
            return items

    @staticmethod
    def remove_from_cart(trip_id: str, cart_item_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM cart_items WHERE trip_id = ? AND id = ?",
                (trip_id, cart_item_id),
            )

    @staticmethod
    def clear_cart(trip_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM cart_items WHERE trip_id = ?", (trip_id,))

    @staticmethod
    def calculate_cart_budget(trip_id: str, budget_ceiling: float | None = None) -> ItemizedBudget:
        items = CommerceService.get_cart_items(trip_id)
        budget_items = []
        for it in items:
            cat = it.type if it.type in ["flight", "hotel", "food", "local_transportation", "activities", "insurance"] else "miscellaneous"
            budget_items.append(
                BudgetItem(
                    name=it.name,
                    category=cat,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total=it.total_price,
                )
            )

        return BudgetEngine.build_itemized_budget(
            duration_days=3,
            travelers=1,
            budget_ceiling=budget_ceiling,
            custom_items=budget_items,
        )
