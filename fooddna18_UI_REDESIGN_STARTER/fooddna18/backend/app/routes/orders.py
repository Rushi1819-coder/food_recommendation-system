"""
FoodDNA - Customer Order Routes (Phase 6).

Customer endpoints for ordering and order lifecycle:
- Place order (checkout with atomic database transaction)
- Customer order history with pagination
- Individual order details (isolated to authenticated customer)
- Order status & timeline tracking
"""

from flask import Blueprint, jsonify, request

from ..middleware.auth import csrf_protected, role_required
from ..services import order_service
from ..services.order_service import (
    EmptyCartError,
    OrderValidationError,
)
from ..utils.query_params import (
    QueryParamError,
    parse_pagination,
    parse_positive_int,
)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def _fail(message, status=400, **extra):
    return jsonify({"success": False, "error": message, **extra}), status


@orders_bp.post("")
@role_required("customer")
@csrf_protected
def checkout(user):
    """
    POST /api/orders
    Body: {
        "delivery_address": "Flat 302, Green Meadows, 5th Cross, Bangalore",
        "payment_method": "cash_on_delivery"
    }
    Places an order atomically from the customer's active cart.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("Request body must be a JSON object.")

    delivery_address = data.get("delivery_address")
    if not delivery_address or not isinstance(delivery_address, str):
        return _fail("delivery_address is required and must be text.")

    payment_method = data.get("payment_method", "cash_on_delivery")
    if not payment_method or not isinstance(payment_method, str):
        return _fail("payment_method must be text.")

    try:
        offer_id = data.get("offer_id")
        order_summary = order_service.place_order(
            user_id=user.id,
            delivery_address=delivery_address,
            payment_method=payment_method,
            offer_id=offer_id,
        )
        return jsonify({
            "success": True,
            "message": "Order placed successfully.",
            "order": order_summary,
        }), 201
    except EmptyCartError as err:
        return _fail(str(err), 400, code="EMPTY_CART")
    except OrderValidationError as err:
        return _fail(str(err), 400)
    except Exception as exc:
        return _fail("Failed to process checkout. Please try again.", 500)


@orders_bp.get("")
@role_required("customer")
def list_orders(user):
    """
    GET /api/orders?page=1&page_size=10
    Retrieves the authenticated customer's previous orders.
    """
    try:
        page, page_size = parse_pagination(request.args)
    except QueryParamError as err:
        return _fail(str(err))

    orders, pagination = order_service.list_customer_orders(
        user_id=user.id,
        page=page,
        page_size=page_size,
    )
    return jsonify({
        "success": True,
        "orders": orders,
        "pagination": pagination,
    })


@orders_bp.get("/<order_id>")
@role_required("customer")
def order_details(user, order_id):
    """
    GET /api/orders/<order_id>
    Retrieves full details of one order belonging to the customer.
    Returns 404 if order does not exist or belongs to another user.
    """
    try:
        parsed_id = parse_positive_int(order_id, "order id")
    except QueryParamError as err:
        return _fail(str(err))
    if parsed_id is None:
        return _fail("order id must be a positive whole number.")

    order = order_service.get_order_details(user_id=user.id, order_id=parsed_id)
    if order is None:
        return _fail("Order not found.", 404)

    return jsonify({
        "success": True,
        "order": order,
    })


@orders_bp.get("/<order_id>/status")
@role_required("customer")
def order_status(user, order_id):
    """
    GET /api/orders/<order_id>/status
    Retrieves current order status and status history for the customer's order.
    """
    try:
        parsed_id = parse_positive_int(order_id, "order id")
    except QueryParamError as err:
        return _fail(str(err))
    if parsed_id is None:
        return _fail("order id must be a positive whole number.")

    status_data = order_service.get_order_status(user_id=user.id, order_id=parsed_id)
    if status_data is None:
        return _fail("Order not found.", 404)

    return jsonify({
        "success": True,
        "status": status_data,
    })
