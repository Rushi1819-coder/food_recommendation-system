"""
FoodDNA - Order & Checkout Service (Phase 6).

Implements transactional order creation and order lifecycle retrieval:
- Strict validation of cart items, meal availability, category and restaurant approval.
- Server-side Decimal recalculation of prices, line totals, subtotal, delivery fee and grand total.
- Atomically creates Order, OrderItem, OrderStatusHistory, Payment, records Food Memory event,
  and clears cart items within a single database transaction.
- Rolls back completely on failure (no partial orders, orphaned payments or unlinked Food Memory).
- Supports Cash on Delivery with initial 'pending' payment status.
- Provides customer order history and detailed order tracking.
"""

from datetime import datetime, date
from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import (
    Cart,
    CartItem,
    FoodCategory,
    Meal,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Restaurant,
    Offer,
    Notification,
)
from ..utils.query_params import pagination_block
from . import food_memory_service
from .cart_service import get_default_delivery_fee
from .restaurant_service import PUBLIC_RESTAURANT_STATUS

MIN_ADDRESS_LENGTH = 10
MAX_ADDRESS_LENGTH = 500
SUPPORTED_PAYMENT_METHODS = {"cash_on_delivery"}


class OrderValidationError(Exception):
    """Raised when checkout validation fails."""
    pass


class EmptyCartError(OrderValidationError):
    """Raised when attempting to checkout with an empty cart."""
    pass


def _money(value):
    """Format decimal monetary values to 2 decimal places."""
    return str(Decimal(value).quantize(Decimal("0.01")))


def validate_delivery_address(address):
    """Validate customer delivery address string."""
    if not isinstance(address, str):
        raise OrderValidationError("Delivery address must be text.")
    cleaned = address.strip()
    if len(cleaned) < MIN_ADDRESS_LENGTH:
        raise OrderValidationError(
            f"Delivery address is too short (minimum {MIN_ADDRESS_LENGTH} characters required)."
        )
    if len(cleaned) > MAX_ADDRESS_LENGTH:
        raise OrderValidationError(
            f"Delivery address is too long (maximum {MAX_ADDRESS_LENGTH} characters allowed)."
        )
    return cleaned


def validate_payment_method(method):
    """Validate selected payment method."""
    if not isinstance(method, str) or method.strip().lower() not in SUPPORTED_PAYMENT_METHODS:
        raise OrderValidationError(
            "Currently only Cash on Delivery ('cash_on_delivery') is supported."
        )
    return method.strip().lower()


def place_order(user_id, delivery_address, payment_method="cash_on_delivery", offer_id=None):
    """
    Atomically places an order from the customer's cart:
    1. Validates delivery address and payment method.
    2. Retrieves customer cart and verifies it contains items.
    3. Revalidates every meal, category, and restaurant in MySQL.
    4. Re-calculates unit prices, subtotal, delivery fee, and grand total.
    5. In one transaction:
       - Creates Order record.
       - Creates OrderItem records with snapshot unit prices.
       - Creates initial OrderStatusHistory record ('pending').
       - Creates Payment record ('pending' Cash on Delivery).
       - Records Food Memory 'order_placed' event.
       - Clears CartItem rows for the customer.
    6. Commits safely. On error, rolls back completely.
    """
    cleaned_address = validate_delivery_address(delivery_address)
    validated_payment_method = validate_payment_method(payment_method)

    # 1. Retrieve cart
    cart = Cart.query.filter_by(user_id=user_id).first()
    if cart is None or not cart.items:
        raise EmptyCartError("Your cart is empty. Please add items before checking out.")

    cart_items = list(cart.items)
    if not cart_items:
        raise EmptyCartError("Your cart is empty. Please add items before checking out.")

    # 2. Verify all items belong to one restaurant and revalidate items
    restaurant_id = None
    subtotal = Decimal("0.00")
    order_items_payload = []

    for item in cart_items:
        # Re-fetch fresh meal state from database
        meal = (
            db.session.query(Meal)
            .join(Restaurant, Restaurant.id == Meal.restaurant_id)
            .join(FoodCategory, FoodCategory.id == Meal.category_id)
            .filter(Meal.id == item.meal_id)
            .first()
        )
        if meal is None:
            raise OrderValidationError(f"Item #{item.id} is no longer available.")

        if not meal.is_available:
            raise OrderValidationError(f"'{meal.name}' is currently out of stock.")

        if not meal.category or not meal.category.is_active:
            raise OrderValidationError(f"'{meal.name}' belongs to an inactive category.")

        if not meal.restaurant or meal.restaurant.status != PUBLIC_RESTAURANT_STATUS:
            raise OrderValidationError(
                f"'{meal.name}' belongs to a restaurant that is not currently approved."
            )

        if restaurant_id is None:
            restaurant_id = meal.restaurant_id
        elif restaurant_id != meal.restaurant_id:
            raise OrderValidationError(
                "All items in the cart must belong to the same restaurant."
            )

        unit_price = Decimal(meal.price).quantize(Decimal("0.01"))
        line_total = (unit_price * Decimal(item.quantity)).quantize(Decimal("0.01"))
        subtotal += line_total

        order_items_payload.append({
            "meal": meal,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    # 3. Calculate final amounts server-side
    delivery_fee = get_default_delivery_fee()
    selected_offer = None
    discount_amount = Decimal("0.00")
    if offer_id is not None:
        if isinstance(offer_id, bool):
            raise OrderValidationError("offer_id must be a valid offer ID.")
        try:
            parsed_offer_id = int(offer_id)
        except (TypeError, ValueError):
            raise OrderValidationError("offer_id must be a valid offer ID.")
        if parsed_offer_id < 1:
            raise OrderValidationError("offer_id must be a valid offer ID.")
        selected_offer = db.session.get(Offer, parsed_offer_id)
        today = date.today()
        if (selected_offer is None or not selected_offer.is_active
                or selected_offer.restaurant_id != restaurant_id
                or selected_offer.start_date > today or selected_offer.end_date < today):
            raise OrderValidationError("The selected offer is not currently valid for this restaurant.")
        discount_amount = (subtotal * Decimal(selected_offer.discount_percent) / Decimal("100")).quantize(Decimal("0.01"))
    total_amount = (subtotal - discount_amount + delivery_fee).quantize(Decimal("0.01"))

    # 4. Atomic transaction
    try:
        order = Order(
            user_id=user_id,
            restaurant_id=restaurant_id,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            order_status="pending",
            delivery_address=cleaned_address,
            placed_at=datetime.utcnow(),
            offer_id=selected_offer.id if selected_offer else None,
            discount_amount=discount_amount,
        )
        db.session.add(order)
        db.session.flush()  # Obtain order.id

        # Order Items
        for item_data in order_items_payload:
            order_item = OrderItem(
                order_id=order.id,
                meal_id=item_data["meal"].id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            db.session.add(order_item)

        # Initial Status History
        history = OrderStatusHistory(
            order_id=order.id,
            status="pending",
            changed_by=user_id,
            note="Order placed with Cash on Delivery.",
        )
        db.session.add(history)

        # Payment record (Pending Cash on Delivery)
        payment = Payment(
            order_id=order.id,
            customer_id=user_id,
            amount=total_amount,
            payment_method=validated_payment_method,
            transaction_id=None,
            payment_status="pending",
            payment_date=None,
        )
        db.session.add(payment)
        db.session.add(Notification(
            user_id=user_id, title=f"Order #{order.id} placed",
            message="Your order was placed successfully. Payment is due on delivery.",
            notification_type="order_placed", is_read=False,
        ))

        # Food Memory event (commit=False to join this transaction)
        food_memory_service.record_event(
            user_id=user_id,
            event_type="order_placed",
            meal_id=None,
            restaurant_id=restaurant_id,
            data={
                "order_id": order.id,
                "total_amount": str(total_amount),
                "item_count": len(order_items_payload),
            },
            commit=False,
        )

        # Clear cart items safely
        CartItem.query.filter_by(cart_id=cart.id).delete()

        # Commit everything together
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise exc

    return serialize_order_summary(order)


def serialize_order_summary(order):
    """Serialize basic order summary."""
    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "restaurant_name": order.restaurant.name if order.restaurant else "Unknown",
        "subtotal": _money(order.subtotal),
        "discount_amount": _money(getattr(order, "discount_amount", 0) or 0),
        "offer_id": getattr(order, "offer_id", None),
        "delivery_fee": _money(order.delivery_fee),
        "total_amount": _money(order.total_amount),
        "order_status": order.order_status,
        "payment_method": order.payment.payment_method if order.payment else "cash_on_delivery",
        "payment_status": order.payment.payment_status if order.payment else "pending",
        "delivery_address": order.delivery_address,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "item_count": sum(i.quantity for i in order.items) if order.items else 0,
    }


def list_customer_orders(user_id, page=1, page_size=10):
    """Retrieve paginated order history for the authenticated customer."""
    query = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc())
    total = query.count()
    orders = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    data = []
    for o in orders:
        items_summary = [f"{item.meal.name} x{item.quantity}" for item in o.items if item.meal][:3]
        total_qty = sum(item.quantity for item in o.items)
        data.append({
            "id": o.id,
            "restaurant_id": o.restaurant_id,
            "restaurant_name": o.restaurant.name if o.restaurant else "Unknown",
            "order_status": o.order_status,
            "total_amount": _money(o.total_amount),
            "subtotal": _money(o.subtotal),
            "delivery_fee": _money(o.delivery_fee),
            "placed_at": o.placed_at.isoformat() if o.placed_at else None,
            "item_count": total_qty,
            "items_summary": items_summary,
            "payment_status": o.payment.payment_status if o.payment else "pending",
            "payment_method": o.payment.payment_method if o.payment else "cash_on_delivery",
        })

    return data, pagination_block(page, page_size, total)


def get_order_details(user_id, order_id):
    """
    Retrieve full details for an order belonging to the customer.
    Returns None if order does not exist or belongs to another user (404).
    """
    order = Order.query.filter_by(id=order_id).first()
    if order is None or order.user_id != user_id:
        return None

    items_data = []
    for item in order.items:
        meal = item.meal
        line_total = (Decimal(item.unit_price) * Decimal(item.quantity)).quantize(Decimal("0.01"))
        items_data.append({
            "id": item.id,
            "meal_id": item.meal_id,
            "name": meal.name if meal else "Dish unavailable",
            "quantity": item.quantity,
            "unit_price": _money(item.unit_price),
            "line_total": _money(line_total),
            "food_type": meal.food_type if meal else None,
            "image_url": meal.image_url if meal else None,
        })

    status_history_data = []
    for sh in order.status_history:
        status_history_data.append({
            "status": sh.status,
            "note": sh.note,
            "created_at": sh.created_at.isoformat() if sh.created_at else None,
        })

    restaurant_data = None
    if order.restaurant:
        restaurant_data = {
            "id": order.restaurant.id,
            "name": order.restaurant.name,
            "address": order.restaurant.address,
            "phone": order.restaurant.phone,
        }

    payment_data = None
    if order.payment:
        payment_data = {
            "amount": _money(order.payment.amount),
            "payment_method": order.payment.payment_method,
            "payment_status": order.payment.payment_status,
            "payment_date": order.payment.payment_date.isoformat() if order.payment.payment_date else None,
        }

    return {
        "id": order.id,
        "order_status": order.order_status,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "delivery_address": order.delivery_address,
        "subtotal": _money(order.subtotal),
        "discount_amount": _money(getattr(order, "discount_amount", 0) or 0),
        "offer_id": getattr(order, "offer_id", None),
        "delivery_fee": _money(order.delivery_fee),
        "total_amount": _money(order.total_amount),
        "restaurant": restaurant_data,
        "items": items_data,
        "payment": payment_data,
        "status_history": status_history_data,
    }


def get_order_status(user_id, order_id):
    """Retrieve status and status history for an order belonging to the customer."""
    order = Order.query.filter_by(id=order_id).first()
    if order is None or order.user_id != user_id:
        return None

    return {
        "id": order.id,
        "order_status": order.order_status,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "status_history": [
            {
                "status": sh.status,
                "note": sh.note,
                "created_at": sh.created_at.isoformat() if sh.created_at else None,
            }
            for sh in order.status_history
        ],
    }
