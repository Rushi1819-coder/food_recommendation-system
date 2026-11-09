"""
Phase 6: Order Placement, Checkout, History and Tracking Tests.

WRITTEN BUT NOT YET EXECUTED (the project owner runs the full suite in the
dedicated testing phase). Expectations may contain mistakes.
"""

from decimal import Decimal
import pytest
from unittest.mock import patch

from app.extensions import db
from app.models import (
    Cart,
    CartItem,
    FoodMemory,
    Meal,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Restaurant,
)
from tests.conftest import csrf_headers, login, make_user
from tests.test_browsing import add_category, add_meal, add_restaurant


@pytest.fixture()
def catalog(app):
    r = add_restaurant("Tandoor Mahal", status="approved")
    cat = add_category("Biryanis", active=True)
    m1 = add_meal(r, cat, "Dum Biryani", "280.00")
    m2 = add_meal(r, cat, "Raita", "40.00")
    db.session.commit()
    return {"restaurant": r, "cat": cat, "m1": m1, "m2": m2}


def as_customer(client, email="buyer@example.com"):
    user = make_user(email, role="customer")
    assert login(client, email).status_code == 200
    return user, csrf_headers(client)


# ============================================================================
# Checkout Validation
# ============================================================================

def test_checkout_with_empty_cart_fails(client):
    user, headers = as_customer(client, "empty_checkout_user@example.com")
    res = client.post(
        "/api/orders",
        json={"delivery_address": "123 MG Road, Bengaluru, Karnataka, 560001"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "empty" in res.get_json()["error"].lower()


def test_invalid_delivery_address_rejected(client, catalog):
    user, headers = as_customer(client, "bad_address_user@example.com")
    # Add an item to cart
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)

    # Too short (< 10 chars)
    res_short = client.post("/api/orders", json={"delivery_address": "Too short"}, headers=headers)
    assert res_short.status_code == 400
    assert "short" in res_short.get_json()["error"].lower()

    # Empty
    res_empty = client.post("/api/orders", json={"delivery_address": "   "}, headers=headers)
    assert res_empty.status_code == 400

    # Non-string
    res_num = client.post("/api/orders", json={"delivery_address": 12345}, headers=headers)
    assert res_num.status_code == 400


# ============================================================================
# Order Placement & Server-Side Pricing
# ============================================================================

def test_checkout_with_valid_cart_places_order_successfully(client, catalog):
    user, headers = as_customer(client, "valid_order_user@example.com")
    # Add 2 Biryani (280 * 2 = 560) and 1 Raita (40 * 1 = 40) -> Subtotal = 600.00
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 2}, headers=headers)
    client.post("/api/cart/items", json={"meal_id": catalog["m2"].id, "quantity": 1}, headers=headers)

    valid_address = "Apartment 4B, Palm Grove Residency, Indiranagar, Bangalore"
    res = client.post(
        "/api/orders",
        json={
            "delivery_address": valid_address,
            "payment_method": "cash_on_delivery",
            # Attempting client-side price tampering (must be ignored)
            "subtotal": "10.00",
            "total_amount": "10.00",
            "delivery_fee": "0.00",
        },
        headers=headers,
    )
    assert res.status_code == 201
    order_data = res.get_json()["order"]

    assert order_data["subtotal"] == "600.00"
    assert order_data["delivery_fee"] == "40.00"
    assert order_data["total_amount"] == "640.00"
    assert order_data["order_status"] == "pending"
    assert order_data["payment_method"] == "cash_on_delivery"
    assert order_data["payment_status"] == "pending"
    assert order_data["delivery_address"] == valid_address
    assert order_data["item_count"] == 3


def test_order_items_and_payment_records_created(client, catalog):
    user, headers = as_customer(client, "records_check_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)

    res = client.post(
        "/api/orders",
        json={"delivery_address": "Flat 101, Lotus Towers, Koramangala, Bangalore"},
        headers=headers,
    )
    assert res.status_code == 201
    order_id = res.get_json()["order"]["id"]

    # Verify Order in MySQL
    order = db.session.get(Order, order_id)
    assert order is not None
    assert order.restaurant_id == catalog["restaurant"].id
    assert order.order_status == "pending"

    # Verify OrderItems
    assert len(order.items) == 1
    item = order.items[0]
    assert item.meal_id == catalog["m1"].id
    assert item.quantity == 1
    assert str(item.unit_price) == "280.00"

    # Verify OrderStatusHistory
    assert len(order.status_history) == 1
    assert order.status_history[0].status == "pending"
    assert order.status_history[0].changed_by == user.id

    # Verify Payment (Cash on Delivery, pending, amount matching total)
    assert order.payment is not None
    assert order.payment.payment_method == "cash_on_delivery"
    assert order.payment.payment_status == "pending"
    assert order.payment.transaction_id is None
    assert order.payment.amount == order.total_amount


def test_cart_cleared_after_successful_checkout(client, catalog):
    user, headers = as_customer(client, "cart_cleared_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)

    client.post(
        "/api/orders",
        json={"delivery_address": "Villa 12, Green Glen Layout, Bellandur, Bangalore"},
        headers=headers,
    )

    # Cart must now be empty
    cart_res = client.get("/api/cart")
    assert cart_res.get_json()["cart"]["is_empty"] is True

    # User's Cart model record must still exist
    cart_row = Cart.query.filter_by(user_id=user.id).first()
    assert cart_row is not None


def test_duplicate_checkout_submission_fails_safely(client, catalog):
    user, headers = as_customer(client, "duplicate_submit_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)

    address = "45 Residency Road, Ashok Nagar, Bangalore, 560025"
    res1 = client.post("/api/orders", json={"delivery_address": address}, headers=headers)
    assert res1.status_code == 201

    # Second immediate submit must fail because cart was cleared
    res2 = client.post("/api/orders", json={"delivery_address": address}, headers=headers)
    assert res2.status_code == 400
    assert "empty" in res2.get_json()["error"].lower()

    # Only 1 order created in database
    assert Order.query.filter_by(user_id=user.id).count() == 1


# ============================================================================
# Transaction Rollback Safety
# ============================================================================

def test_transaction_rollback_when_order_creation_fails(client, catalog, app):
    user, headers = as_customer(client, "rollback_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)

    # Simulate an error during OrderItem creation
    with patch("app.services.order_service.food_memory_service.record_event", side_effect=RuntimeError("Simulated failure")):
        res = client.post(
            "/api/orders",
            json={"delivery_address": "Test Address 12345, Bengaluru"},
            headers=headers,
        )
        assert res.status_code == 500

    # Ensure no partial order, items, payments or memories were persisted
    assert Order.query.filter_by(user_id=user.id).count() == 0
    assert Payment.query.filter_by(customer_id=user.id).count() == 0
    assert FoodMemory.query.filter_by(user_id=user.id, event_type="order_placed").count() == 0

    # Cart items must still be preserved because order failed
    cart_res = client.get("/api/cart")
    assert cart_res.get_json()["cart"]["is_empty"] is False


# ============================================================================
# Order History & Details Retrieval
# ============================================================================

def test_customer_order_history_and_pagination(client, catalog):
    user, headers = as_customer(client, "history_user@example.com")
    address = "Test Street 100, HSR Layout, Bengaluru"

    # Place 2 orders
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers)
    client.post("/api/orders", json={"delivery_address": address}, headers=headers)

    client.post("/api/cart/items", json={"meal_id": catalog["m2"].id, "quantity": 2}, headers=headers)
    client.post("/api/orders", json={"delivery_address": address}, headers=headers)

    res = client.get("/api/orders?page=1&page_size=10")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["orders"]) == 2
    assert data["pagination"]["total"] == 2
    assert data["orders"][0]["id"] > data["orders"][1]["id"]  # newest first


def test_customer_order_details(client, catalog):
    user, headers = as_customer(client, "details_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 2}, headers=headers)
    order_res = client.post(
        "/api/orders",
        json={"delivery_address": "Suite 900, Prestige Towers, Bangalore"},
        headers=headers,
    )
    order_id = order_res.get_json()["order"]["id"]

    res = client.get(f"/api/orders/{order_id}")
    assert res.status_code == 200
    details = res.get_json()["order"]
    assert details["id"] == order_id
    assert details["restaurant"]["name"] == catalog["restaurant"].name
    assert len(details["items"]) == 1
    assert details["items"][0]["quantity"] == 2
    assert len(details["status_history"]) >= 1
    assert details["payment"]["payment_method"] == "cash_on_delivery"
    assert details["payment"]["payment_status"] == "pending"


def test_customer_cannot_access_another_customers_order(client, catalog):
    user_a, headers_a = as_customer(client, "cust_a@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 1}, headers=headers_a)
    order_res = client.post(
        "/api/orders",
        json={"delivery_address": "Address A, Indiranagar, Bangalore"},
        headers=headers_a,
    )
    order_id = order_res.get_json()["order"]["id"]

    # Customer B tries to view Customer A's order
    user_b, headers_b = as_customer(client, "cust_b@example.com")
    res = client.get(f"/api/orders/{order_id}")
    assert res.status_code == 404

    status_res = client.get(f"/api/orders/{order_id}/status")
    assert status_res.status_code == 404


def test_food_memory_records_order_placed_event(client, catalog):
    user, headers = as_customer(client, "fm_order_user@example.com")
    client.post("/api/cart/items", json={"meal_id": catalog["m1"].id, "quantity": 2}, headers=headers)
    res = client.post(
        "/api/orders",
        json={"delivery_address": "12 Richmond Road, Bangalore"},
        headers=headers,
    )
    order_id = res.get_json()["order"]["id"]

    event = FoodMemory.query.filter_by(user_id=user.id, event_type="order_placed").first()
    assert event is not None
    assert event.restaurant_id == catalog["restaurant"].id
    assert event.event_data["order_id"] == order_id
    assert event.event_data["total_amount"] == "600.00"
