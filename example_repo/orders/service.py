"""Order service: creation, pricing, and state transitions.

Orchestrates storage.repository, pricing.rules, and pricing.vouchers.
"""
from __future__ import annotations
import uuid
from storage.models import Order, OrderItem
from storage.repository import OrderRepository, ProductRepository, CustomerRepository
from pricing.rules import calculate_item_price
from pricing.vouchers import validate_voucher, apply_discount


class OrderService:
    """Creates and manages orders for a customer."""

    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        customers: CustomerRepository,
    ) -> None:
        self._orders = orders
        self._products = products
        self._customers = customers

    def create_order(self, customer_id: str) -> Order:
        """Create an empty pending order for a customer."""
        order = Order(id=str(uuid.uuid4()), customer_id=customer_id)
        self._orders.save(order)
        return order

    def add_item(self, order_id: str, product_id: str, quantity: int) -> bool:
        """Append a product to an existing order at the correct tier-priced rate."""
        order = self._orders.get(order_id)
        if order is None or order.status != "pending":
            return False
        product = self._products.get(product_id)
        if product is None:
            return False
        customer = self._customers.get(order.customer_id)
        tier = customer.tier if customer else "standard"

        # Indirect call chain: add_item → calculate_item_price → apply_discount + apply_tax
        unit_price = calculate_item_price(product.base_price, product.category, tier)
        order.items.append(OrderItem(product_id=product_id, quantity=quantity, unit_price=unit_price))
        order.total = sum(item.subtotal for item in order.items)
        self._orders.save(order)
        return True

    def apply_voucher(self, order_id: str, code: str) -> bool:
        """Apply a voucher to an order if valid."""
        if not validate_voucher(code):
            return False
        order = self._orders.get(order_id)
        if order is None or order.status != "pending":
            return False
        # Indirect call chain: apply_voucher → apply_discount (vouchers.apply_discount)
        order.total = apply_discount(order.total, code)
        self._orders.save(order)
        return True

    def confirm_order(self, order_id: str) -> bool:
        """Transition a pending order to confirmed."""
        return self._orders.update_status(order_id, "confirmed")

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or confirmed order."""
        order = self._orders.get(order_id)
        if order is None or order.status not in ("pending", "confirmed"):
            return False
        return self._orders.update_status(order_id, "cancelled")

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)
