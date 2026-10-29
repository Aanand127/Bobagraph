"""Tests for orders.service — order lifecycle and pricing integration."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.models import Customer, Product
from storage.repository import CustomerRepository, OrderRepository, ProductRepository
from orders.service import OrderService


def _make_service():
    orders = OrderRepository()
    products = ProductRepository()
    customers = CustomerRepository()
    return OrderService(orders, products, customers), orders, products, customers


def _seed(products, customers):
    products.save(Product(id="p1", name="Laptop", base_price=1000.0, category="electronics"))
    products.save(Product(id="p2", name="Apple", base_price=1.0, category="food"))
    customers.save(Customer(id="c1", name="Alice", tier="platinum"))
    customers.save(Customer(id="c2", name="Bob", tier="standard"))


def test_create_order_returns_pending():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    assert order.status == "pending"
    assert order.customer_id == "c1"


def test_add_item_updates_total():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    ok = svc.add_item(order.id, "p2", 3)
    assert ok is True
    updated = svc.get_order(order.id)
    # platinum tier: 20% off food (no tax) = 1.0 * 0.8 * 3 = 2.4
    assert updated.total == pytest.approx(2.4, rel=1e-3)


def test_add_item_to_nonexistent_order_fails():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    assert svc.add_item("no-such-order", "p1", 1) is False


def test_add_item_unknown_product_fails():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    assert svc.add_item(order.id, "unknown", 1) is False


def test_apply_valid_voucher_reduces_total():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c2")
    svc.add_item(order.id, "p1", 1)  # standard tier, electronics: 1000 * 1.08 = 1080
    ok = svc.apply_voucher(order.id, "SAVE25")
    assert ok is True
    updated = svc.get_order(order.id)
    assert updated.total == pytest.approx(1055.0, rel=1e-3)


def test_apply_invalid_voucher_returns_false():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    assert svc.apply_voucher(order.id, "BOGUS") is False


def test_confirm_order_changes_status():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    assert svc.confirm_order(order.id) is True
    assert svc.get_order(order.id).status == "confirmed"


def test_cancel_confirmed_order():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    svc.confirm_order(order.id)
    assert svc.cancel_order(order.id) is True
    assert svc.get_order(order.id).status == "cancelled"


def test_add_item_to_confirmed_order_fails():
    svc, _, products, customers = _make_service()
    _seed(products, customers)
    order = svc.create_order("c1")
    svc.confirm_order(order.id)
    assert svc.add_item(order.id, "p1", 1) is False


import pytest
