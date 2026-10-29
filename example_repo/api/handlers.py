"""HTTP API entry point: routes incoming requests to the order service."""
from __future__ import annotations
from dataclasses import dataclass
from orders.service import OrderService
from orders.summary import format_summary, get_status
from storage.models import Customer, Product


@dataclass
class Request:
    method: str
    path: str
    body: dict


@dataclass
class Response:
    status: int
    body: dict


class OrderAPI:
    """Thin HTTP-style handler that delegates to OrderService."""

    def __init__(self, service: OrderService) -> None:
        self._service = service

    def handle(self, request: Request) -> Response:
        """Route a request by method + path."""
        if request.method == "POST" and request.path == "/orders":
            return self._create_order(request)
        if request.method == "POST" and request.path.endswith("/items"):
            return self._add_item(request)
        if request.method == "POST" and request.path.endswith("/voucher"):
            return self._apply_voucher(request)
        if request.method == "POST" and request.path.endswith("/confirm"):
            return self._confirm(request)
        if request.method == "GET" and request.path.startswith("/orders/"):
            return self._get_order(request)
        return Response(status=404, body={"error": "not found"})

    # --- private handlers --------------------------------------------------

    def _create_order(self, request: Request) -> Response:
        customer_id = request.body.get("customer_id", "")
        if not customer_id:
            return Response(status=400, body={"error": "customer_id required"})
        order = self._service.create_order(customer_id)
        return Response(status=201, body={"order_id": order.id, "status": order.status})

    def _add_item(self, request: Request) -> Response:
        # path: /orders/<id>/items
        parts = request.path.split("/")
        order_id = parts[2] if len(parts) >= 3 else ""
        product_id = request.body.get("product_id", "")
        quantity = int(request.body.get("quantity", 0))
        ok = self._service.add_item(order_id, product_id, quantity)
        if not ok:
            return Response(status=400, body={"error": "add_item failed"})
        order = self._service.get_order(order_id)
        return Response(status=200, body={"total": order.total})

    def _apply_voucher(self, request: Request) -> Response:
        parts = request.path.split("/")
        order_id = parts[2] if len(parts) >= 3 else ""
        code = request.body.get("code", "")
        ok = self._service.apply_voucher(order_id, code)
        return Response(status=200 if ok else 400, body={"applied": ok})

    def _confirm(self, request: Request) -> Response:
        parts = request.path.split("/")
        order_id = parts[2] if len(parts) >= 3 else ""
        ok = self._service.confirm_order(order_id)
        return Response(status=200 if ok else 400, body={"confirmed": ok})

    def _get_order(self, request: Request) -> Response:
        order_id = request.path.split("/")[2]
        order = self._service.get_order(order_id)
        if order is None:
            return Response(status=404, body={"error": "order not found"})
        return Response(
            status=200,
            body={
                "summary": format_summary(order),
                "status": get_status(order),
                "total": order.total,
            },
        )
