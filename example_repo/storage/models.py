"""In-memory storage models for orders and products."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """A product available for purchase."""
    id: str
    name: str
    base_price: float
    category: str


@dataclass
class Order:
    """A placed order.  status: pending | confirmed | shipped | cancelled."""
    id: str
    customer_id: str
    items: list[OrderItem] = field(default_factory=list)
    status: str = "pending"
    total: float = 0.0


@dataclass
class OrderItem:
    """One line-item in an order."""
    product_id: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Customer:
    """A registered customer with an optional loyalty tier."""
    id: str
    name: str
    tier: str = "standard"  # standard | gold | platinum
