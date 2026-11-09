"""
FoodDNA - Shopping Cart Routes (Phase 6).

Customer endpoints for managing the shopping cart:
- View cart contents and charges
- Add meals (with single-restaurant enforcement and HTTP 409 on conflict)
- Update item quantities
- Remove items
- Clear entire cart
"""

from flask import Blueprint, jsonify, request

from ..middleware.auth import csrf_protected, role_required
from ..services import cart_service
from ..services.cart_service import (
    CartRestaurantConflictError,
    MealUnavailableError,
)
from ..utils.query_params import QueryParamError, parse_positive_int

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")


def _fail(message, status=400, **extra):
    return jsonify({"success": False, "error": message, **extra}), status


@cart_bp.get("")
@role_required("customer")
def get_cart(user):
    """
    GET /api/cart
    Retrieve the authenticated customer's current cart and authoritative totals.
    """
    cart_data = cart_service.get_cart_for_user(user.id)
    return jsonify({
        "success": True,
        "cart": cart_data,
        "message": "Cart is empty." if cart_data["is_empty"] else "Cart retrieved.",
    })


@cart_bp.post("/items")
@role_required("customer")
@csrf_protected
def add_item(user):
    """
    POST /api/cart/items
    Body: {"meal_id": 10, "quantity": 1}
    Adds an available meal to the cart or increments its quantity.
    Returns HTTP 409 if the meal belongs to a different restaurant.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("Request body must be a JSON object.")

    raw_meal_id = data.get("meal_id")
    if raw_meal_id is None or isinstance(raw_meal_id, bool):
        return _fail("meal_id is required and must be a positive integer.")
    try:
        meal_id = parse_positive_int(str(raw_meal_id), "meal_id")
    except QueryParamError as err:
        return _fail(str(err))
    if meal_id is None:
        return _fail("meal_id must be a positive integer.")

    raw_quantity = data.get("quantity", 1)
    if raw_quantity is None or isinstance(raw_quantity, bool):
        return _fail("quantity must be a positive integer.")
    try:
        quantity = parse_positive_int(str(raw_quantity), "quantity")
    except QueryParamError as err:
        return _fail(str(err))
    if quantity is None:
        return _fail("quantity must be a positive integer.")

    try:
        cart_data = cart_service.add_to_cart(user.id, meal_id, quantity)
        return jsonify({
            "success": True,
            "message": "Item added to cart.",
            "cart": cart_data,
        })
    except CartRestaurantConflictError as conflict:
        return jsonify({
            "success": False,
            "error": str(conflict),
            "code": "RESTAURANT_CONFLICT",
            "existing_restaurant": {
                "id": conflict.existing_restaurant.id,
                "name": conflict.existing_restaurant.name,
            },
            "new_restaurant": {
                "id": conflict.new_restaurant.id,
                "name": conflict.new_restaurant.name,
            },
        }), 409
    except MealUnavailableError as err:
        return _fail(str(err), 400)
    except ValueError as err:
        return _fail(str(err), 400)


@cart_bp.patch("/items/<int:item_id>")
@role_required("customer")
@csrf_protected
def update_item(user, item_id):
    """
    PATCH /api/cart/items/<item_id>
    Body: {"quantity": 3}
    Updates the quantity of a specific cart item.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("Request body must be a JSON object.")

    raw_quantity = data.get("quantity")
    if raw_quantity is None or isinstance(raw_quantity, bool):
        return _fail("quantity is required and must be a positive integer.")
    try:
        quantity = parse_positive_int(str(raw_quantity), "quantity")
    except QueryParamError as err:
        return _fail(str(err))
    if quantity is None:
        return _fail("quantity must be a positive integer.")

    try:
        cart_data = cart_service.update_cart_item_quantity(user.id, item_id, quantity)
        return jsonify({
            "success": True,
            "message": "Cart item updated.",
            "cart": cart_data,
        })
    except LookupError as err:
        return _fail(str(err), 404)
    except (MealUnavailableError, ValueError) as err:
        return _fail(str(err), 400)


@cart_bp.delete("/items/<int:item_id>")
@role_required("customer")
@csrf_protected
def remove_item(user, item_id):
    """
    DELETE /api/cart/items/<item_id>
    Removes a specific item from the authenticated customer's cart.
    """
    try:
        cart_data = cart_service.remove_cart_item(user.id, item_id)
        return jsonify({
            "success": True,
            "message": "Item removed from cart.",
            "cart": cart_data,
        })
    except LookupError as err:
        return _fail(str(err), 404)


@cart_bp.delete("")
@role_required("customer")
@csrf_protected
def clear_cart(user):
    """
    DELETE /api/cart
    Clears all items from the customer's cart.
    """
    cart_data = cart_service.clear_cart(user.id)
    return jsonify({
        "success": True,
        "message": "Cart cleared.",
        "cart": cart_data,
    })
