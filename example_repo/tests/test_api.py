"""Tests for api.handlers — HTTP routing and delegation to service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.models import Customer, Product
from storage.repository import CustomerRepository, OrderRepository, ProductRepository
from orders.service import OrderService
from api.handlers import OrderAPI, Request


def _make_api():
    orders = OrderRepository()
    products = ProductRepository()
    customers = CustomerRepository()
    products.save(Product(id="p1", name="Laptop", base_price=1000.0, category="electronics"))
    customers.save(Customer(id="c1", name="Alice", tier="standard"))
    svc = OrderService(orders, products, customers)
    return OrderAPI(svc), svc


def test_create_order_returns_201():
    api, _ = _make_api()
    resp = api.handle(Request("POST", "/orders", {"customer_id": "c1"}))
    assert resp.status == 201
    assert "order_id" in resp.body


def test_create_order_missing_customer_id_returns_400():
    api, _ = _make_api()
    resp = api.handle(Request("POST", "/orders", {}))
    assert resp.status == 400


def test_add_item_and_get_total():
    api, svc = _make_api()
    create_resp = api.handle(Request("POST", "/orders", {"customer_id": "c1"}))
    order_id = create_resp.body["order_id"]
    add_resp = api.handle(Request("POST", f"/orders/{order_id}/items", {"product_id": "p1", "quantity": 1}))
    assert add_resp.status == 200
    assert add_resp.body["total"] == pytest.approx(1080.0, rel=1e-3)  # standard, electronics 8% tax


def test_apply_voucher_success():
    api, _ = _make_api()
    create_resp = api.handle(Request("POST", "/orders", {"customer_id": "c1"}))
    order_id = create_resp.body["order_id"]
    api.handle(Request("POST", f"/orders/{order_id}/items", {"product_id": "p1", "quantity": 1}))
    voucher_resp = api.handle(Request("POST", f"/orders/{order_id}/voucher", {"code": "SAVE10"}))
    assert voucher_resp.status == 200
    assert voucher_resp.body["applied"] is True


def test_confirm_order():
    api, _ = _make_api()
    create_resp = api.handle(Request("POST", "/orders", {"customer_id": "c1"}))
    order_id = create_resp.body["order_id"]
    confirm_resp = api.handle(Request("POST", f"/orders/{order_id}/confirm", {}))
    assert confirm_resp.status == 200
    assert confirm_resp.body["confirmed"] is True


def test_get_order_returns_summary():
    api, _ = _make_api()
    create_resp = api.handle(Request("POST", "/orders", {"customer_id": "c1"}))
    order_id = create_resp.body["order_id"]
    get_resp = api.handle(Request("GET", f"/orders/{order_id}", {}))
    assert get_resp.status == 200
    assert "summary" in get_resp.body
    assert get_resp.body["status"] == "pending"


def test_get_nonexistent_order_returns_404():
    api, _ = _make_api()
    resp = api.handle(Request("GET", "/orders/no-such-order", {}))
    assert resp.status == 404


def test_unknown_route_returns_404():
    api, _ = _make_api()
    resp = api.handle(Request("DELETE", "/orders", {}))
    assert resp.status == 404


import pytest
