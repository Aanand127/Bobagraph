"""Simple in-memory repository for products, orders and customers."""
from __future__ import annotations
from typing import Optional
from .models import Order, OrderItem, Product, Customer


class ProductRepository:
    """Stores and retrieves Product records."""

    def __init__(self) -> None:
        self._store: dict[str, Product] = {}

    def save(self, product: Product) -> None:
        self._store[product.id] = product

    def get(self, product_id: str) -> Optional[Product]:
        return self._store.get(product_id)

    def all(self) -> list[Product]:
        return list(self._store.values())


class OrderRepository:
    """Stores and retrieves Order records."""

    def __init__(self) -> None:
        self._store: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._store[order.id] = order

    def get(self, order_id: str) -> Optional[Order]:
        return self._store.get(order_id)

    def find_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._store.values() if o.customer_id == customer_id]

    def update_status(self, order_id: str, status: str) -> bool:
        order = self._store.get(order_id)
        if order is None:
            return False
        order.status = status
        return True


class CustomerRepository:
    """Stores and retrieves Customer records."""

    def __init__(self) -> None:
        self._store: dict[str, Customer] = {}

    def save(self, customer: Customer) -> None:
        self._store[customer.id] = customer

    def get(self, customer_id: str) -> Optional[Customer]:
        return self._store.get(customer_id)
