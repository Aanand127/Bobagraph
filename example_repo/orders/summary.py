"""Order summary helpers for display and reporting."""
from __future__ import annotations
from storage.models import Order


def format_summary(order: Order) -> str:
    """Return a human-readable one-line summary of an order."""
    item_count = sum(i.quantity for i in order.items)
    return (
        f"Order {order.id[:8]} | customer={order.customer_id} "
        f"| {item_count} item(s) | total=${order.total:.2f} | {order.status}"
    )


def get_status(order: Order) -> str:
    """Return the current status string of the order."""
    return order.status
