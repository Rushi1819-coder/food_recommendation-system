"""
FoodDNA - Shopping Cart Service (Phase 6).

Handles customer cart operations with strict server-side validation:
- Enforces one restaurant per active cart.
- Authoritatively reads meal prices from MySQL.
- Performs Decimal-compatible arithmetic for line totals, subtotal and delivery fee.
- Enforces quantity constraints (1 to 50 items per meal).
- Preserves the Cart row when cart items are cleared.
- Emits Food Memory 'added_to_cart' events.
"""

from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Cart, CartItem, FoodCategory, Meal, Restaurant
from . import food_memory_service
from .restaurant_service import PUBLIC_RESTAURANT_STATUS

MAX_ITEM_QUANTITY = 50
MIN_ITEM_QUANTITY = 1


class CartRestaurantConflictError(Exception):
    """Raised when adding a dish from a restaurant different from the current cart."""

    def __init__(self, existing_restaurant, new_restaurant):
        self.existing_restaurant = existing_restaurant
        self.new_restaurant = new_restaurant
        super().__init__(
            f"Your cart already contains items from '{existing_restaurant.name}'. "
            f"An order can only be placed from one restaurant at a time. "
            f"Please clear your cart before adding items from '{new_restaurant.name}'."
        )


class MealUnavailableError(Exception):
    """Raised when attempting to add an unavailable or unapproved meal."""
    pass


def _money(value):
    """Format decimal monetary values to 2 decimal places."""
    return str(Decimal(value).quantize(Decimal("0.01")))


def get_default_delivery_fee():
    """Retrieve the configured default delivery fee."""
    fee_str = current_app.config.get("DEFAULT_DELIVERY_FEE", "40.00")
    try:
        return Decimal(str(fee_str)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("40.00")


def get_or_create_cart(user_id):
    """
    Retrieve the active cart for the customer, creating one if it does not exist.
    Handles potential race condition via unique constraint on user_id.
    """
    cart = Cart.query.filter_by(user_id=user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id, status="active")
        db.session.add(cart)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            cart = Cart.query.filter_by(user_id=user_id).first()
    return cart


def serialize_cart(cart):
    """
    Serialize cart contents with calculated line totals, subtotal,
    delivery fee and final amount using Decimal arithmetic.
    """
    items_data = []
    subtotal = Decimal("0.00")
    total_quantity = 0
    restaurant_info = None

    if cart and cart.items:
        for item in cart.items:
            meal = item.meal
            if not meal:
                continue

            unit_price = Decimal(meal.price)
            line_total = (unit_price * Decimal(item.quantity)).quantize(Decimal("0.01"))
            subtotal += line_total
            total_quantity += item.quantity

            if restaurant_info is None and meal.restaurant:
                restaurant_info = {
                    "id": meal.restaurant.id,
                    "name": meal.restaurant.name,
                    "address": meal.restaurant.address,
                }

            items_data.append({
                "id": item.id,
                "meal_id": meal.id,
                "name": meal.name,
                "description": meal.description,
                "price": _money(unit_price),
                "quantity": item.quantity,
                "line_total": _money(line_total),
                "cuisine": meal.cuisine,
                "food_type": meal.food_type,
                "image_url": meal.image_url,
                "is_available": meal.is_available,
                "restaurant_id": meal.restaurant_id,
                "restaurant_name": meal.restaurant.name if meal.restaurant else None,
            })

    is_empty = len(items_data) == 0
    delivery_fee = Decimal("0.00") if is_empty else get_default_delivery_fee()
    total_amount = (subtotal + delivery_fee).quantize(Decimal("0.01"))

    return {
        "cart_id": cart.id if cart else None,
        "is_empty": is_empty,
        "item_count": total_quantity,
        "restaurant": restaurant_info,
        "items": items_data,
        "subtotal": _money(subtotal),
        "delivery_fee": _money(delivery_fee),
        "total_amount": _money(total_amount),
    }


def get_cart_for_user(user_id):
    """Get the customer's serialized cart."""
    cart = get_or_create_cart(user_id)
    return serialize_cart(cart)


def add_to_cart(user_id, meal_id, quantity=1):
    """
    Add a meal to the customer's cart:
    - Validates meal existence and active/available status.
    - Validates restaurant status ('approved').
    - Validates category status ('active').
    - Enforces single restaurant per cart.
    - If meal already exists, increments quantity up to MAX_ITEM_QUANTITY.
    - Records 'added_to_cart' Food Memory event.
    """
    if quantity < MIN_ITEM_QUANTITY or quantity > MAX_ITEM_QUANTITY:
        raise ValueError(
            f"Quantity must be between {MIN_ITEM_QUANTITY} and {MAX_ITEM_QUANTITY}."
        )

    # Validate meal and its restaurant / category
    meal = (
        db.session.query(Meal)
        .join(Restaurant, Restaurant.id == Meal.restaurant_id)
        .join(FoodCategory, FoodCategory.id == Meal.category_id)
        .filter(Meal.id == meal_id)
        .first()
    )
    if meal is None:
        raise MealUnavailableError("The requested dish does not exist.")

    if not meal.is_available:
        raise MealUnavailableError(f"'{meal.name}' is currently unavailable.")

    if not meal.category or not meal.category.is_active:
        raise MealUnavailableError(f"'{meal.name}' belongs to an inactive category.")

    if not meal.restaurant or meal.restaurant.status != PUBLIC_RESTAURANT_STATUS:
        raise MealUnavailableError(
            f"'{meal.name}' belongs to a restaurant that is not currently approved."
        )

    cart = get_or_create_cart(user_id)

    # Check restaurant consistency across existing items
    if cart.items:
        first_meal = cart.items[0].meal
        if first_meal and first_meal.restaurant_id != meal.restaurant_id:
            raise CartRestaurantConflictError(
                existing_restaurant=first_meal.restaurant,
                new_restaurant=meal.restaurant,
            )

    # Check if item already exists in cart
    existing_item = CartItem.query.filter_by(
        cart_id=cart.id, meal_id=meal.id
    ).first()

    if existing_item:
        new_quantity = existing_item.quantity + quantity
        if new_quantity > MAX_ITEM_QUANTITY:
            raise ValueError(
                f"Cannot add {quantity} more. Maximum quantity per dish is {MAX_ITEM_QUANTITY} "
                f"(current: {existing_item.quantity})."
            )
        existing_item.quantity = new_quantity
    else:
        new_item = CartItem(
            cart_id=cart.id,
            meal_id=meal.id,
            quantity=quantity,
        )
        db.session.add(new_item)

    # Record Food Memory event
    food_memory_service.record_event(
        user_id=user_id,
        event_type="added_to_cart",
        meal_id=meal.id,
        restaurant_id=meal.restaurant_id,
        data={"quantity": quantity, "meal_name": meal.name[:100]},
        commit=False,
    )

    db.session.commit()
    return serialize_cart(cart)


def update_cart_item_quantity(user_id, item_id, quantity):
    """
    Update quantity of a specific cart item belonging to the customer.
    """
    if quantity < MIN_ITEM_QUANTITY or quantity > MAX_ITEM_QUANTITY:
        raise ValueError(
            f"Quantity must be between {MIN_ITEM_QUANTITY} and {MAX_ITEM_QUANTITY}."
        )

    cart = get_or_create_cart(user_id)
    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if item is None:
        raise LookupError("Cart item not found or does not belong to your cart.")

    # Revalidate meal availability
    if not item.meal or not item.meal.is_available:
        raise MealUnavailableError("This dish is no longer available.")

    item.quantity = quantity
    db.session.commit()
    return serialize_cart(cart)


def remove_cart_item(user_id, item_id):
    """
    Remove an individual item from the customer's cart.
    """
    cart = get_or_create_cart(user_id)
    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if item is None:
        raise LookupError("Cart item not found or does not belong to your cart.")

    db.session.delete(item)
    db.session.commit()
    return serialize_cart(cart)


def clear_cart(user_id):
    """
    Clear all items from the customer's cart, preserving the cart record itself.
    """
    cart = get_or_create_cart(user_id)
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return serialize_cart(cart)
