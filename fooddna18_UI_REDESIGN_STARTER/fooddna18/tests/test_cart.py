"""
Phase 6: Shopping Cart APIs and Business Logic Tests.

WRITTEN BUT NOT YET EXECUTED (the project owner runs the full suite in the
dedicated testing phase). Expectations may contain mistakes.
"""

from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cart, CartItem, FoodMemory, Meal, Restaurant
from tests.conftest import csrf_headers, login, make_user
from tests.test_browsing import add_category, add_meal, add_restaurant


@pytest.fixture()
def setup_catalog(app):
    r1 = add_restaurant("Spice Garden", status="approved")
    r2 = add_restaurant("Royal Tandoor", status="approved")
    r_unapproved = add_restaurant("Pending Diner", status="pending")
    cat = add_category("Main Course", active=True)
    cat_inactive = add_category("Archived Category", active=False)

    m1 = add_meal(r1, cat, "Butter Chicken", "250.00")
    m2 = add_meal(r1, cat, "Garlic Naan", "50.00")
    m3_diff_rest = add_meal(r2, cat, "Biryani", "300.00")
    m_sold_out = add_meal(r1, cat, "Seasonal Fish", "400.00", is_available=False)
    m_inactive_cat = add_meal(r1, cat_inactive, "Old Recipe", "150.00")
    m_unapproved_rest = add_meal(r_unapproved, cat, "Secret Dish", "120.00")

    db.session.commit()
    return {
        "r1": r1,
        "r2": r2,
        "cat": cat,
        "m1": m1,
        "m2": m2,
        "m3_diff_rest": m3_diff_rest,
        "m_sold_out": m_sold_out,
        "m_inactive_cat": m_inactive_cat,
        "m_unapproved_rest": m_unapproved_rest,
    }


def as_customer(client, email="customer@example.com"):
    user = make_user(email, role="customer")
    assert login(client, email).status_code == 200
    return user, csrf_headers(client)


# ============================================================================
# Cart Retrieval & Empty State
# ============================================================================

def test_empty_cart_returns_valid_structure(client):
    user, _ = as_customer(client, "empty_cart_user@example.com")
    res = client.get("/api/cart")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    cart = data["cart"]
    assert cart["is_empty"] is True
    assert cart["items"] == []
    assert cart["item_count"] == 0
    assert cart["subtotal"] == "0.00"
    assert cart["delivery_fee"] == "0.00"
    assert cart["total_amount"] == "0.00"
    assert cart["restaurant"] is None


# ============================================================================
# Adding Items & Quantity Increments
# ============================================================================

def test_add_available_meal(client, setup_catalog):
    user, headers = as_customer(client, "add_meal_user@example.com")
    meal = setup_catalog["m1"]

    res = client.post(
        "/api/cart/items",
        json={"meal_id": meal.id, "quantity": 2},
        headers=headers,
    )
    assert res.status_code == 200
    cart = res.get_json()["cart"]
    assert cart["is_empty"] is False
    assert len(cart["items"]) == 1
    assert cart["items"][0]["meal_id"] == meal.id
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][0]["price"] == "250.00"
    assert cart["items"][0]["line_total"] == "500.00"
    assert cart["subtotal"] == "500.00"
    assert cart["delivery_fee"] == "40.00"
    assert cart["total_amount"] == "540.00"
    assert cart["restaurant"]["id"] == setup_catalog["r1"].id


def test_add_same_meal_twice_increments_quantity(client, setup_catalog):
    user, headers = as_customer(client, "repeat_item_user@example.com")
    meal = setup_catalog["m1"]

    client.post("/api/cart/items", json={"meal_id": meal.id, "quantity": 1}, headers=headers)
    res = client.post("/api/cart/items", json={"meal_id": meal.id, "quantity": 2}, headers=headers)
    assert res.status_code == 200
    cart = res.get_json()["cart"]
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3
    assert cart["items"][0]["line_total"] == "750.00"


def test_migration_003_unique_constraint_enforced_in_db(app, setup_catalog):
    user = make_user("db_constraint_user@example.com", role="customer")
    cart = Cart(user_id=user.id)
    db.session.add(cart)
    db.session.flush()

    item1 = CartItem(cart_id=cart.id, meal_id=setup_catalog["m1"].id, quantity=1)
    db.session.add(item1)
    db.session.commit()

    # Attempting to insert duplicate row for same cart and meal must fail
    item2 = CartItem(cart_id=cart.id, meal_id=setup_catalog["m1"].id, quantity=2)
    db.session.add(item2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ============================================================================
# Single Restaurant per Cart Enforcement
# ============================================================================

def test_attempting_to_add_meal_from_another_restaurant_returns_409(client, setup_catalog):
    user, headers = as_customer(client, "conflict_cart_user@example.com")
    # Add dish from Restaurant 1
    client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m1"].id, "quantity": 1},
        headers=headers,
    )

    # Attempt to add dish from Restaurant 2
    res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m3_diff_rest"].id, "quantity": 1},
        headers=headers,
    )
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False
    assert data["code"] == "RESTAURANT_CONFLICT"
    assert data["existing_restaurant"]["id"] == setup_catalog["r1"].id
    assert data["new_restaurant"]["id"] == setup_catalog["r2"].id

    # Verify cart remains untouched
    cart_res = client.get("/api/cart")
    cart = cart_res.get_json()["cart"]
    assert len(cart["items"]) == 1
    assert cart["items"][0]["meal_id"] == setup_catalog["m1"].id


# ============================================================================
# Availability & Status Validations
# ============================================================================

def test_add_unavailable_meal_fails(client, setup_catalog):
    user, headers = as_customer(client, "sold_out_user@example.com")
    res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m_sold_out"].id, "quantity": 1},
        headers=headers,
    )
    assert res.status_code == 400
    assert "unavailable" in res.get_json()["error"].lower()


def test_add_meal_from_unapproved_restaurant_fails(client, setup_catalog):
    user, headers = as_customer(client, "unapproved_user@example.com")
    res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m_unapproved_rest"].id, "quantity": 1},
        headers=headers,
    )
    assert res.status_code == 400
    assert "approved" in res.get_json()["error"].lower()


def test_invalid_quantities_rejected(client, setup_catalog):
    user, headers = as_customer(client, "invalid_qty_user@example.com")
    meal = setup_catalog["m1"]

    for bad_qty in [0, -1, 51, "three"]:
        res = client.post(
            "/api/cart/items",
            json={"meal_id": meal.id, "quantity": bad_qty},
            headers=headers,
        )
        assert res.status_code == 400


# ============================================================================
# Updating, Removing and Clearing
# ============================================================================

def test_update_item_quantity(client, setup_catalog):
    user, headers = as_customer(client, "update_qty_user@example.com")
    add_res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m1"].id, "quantity": 1},
        headers=headers,
    )
    item_id = add_res.get_json()["cart"]["items"][0]["id"]

    res = client.patch(
        f"/api/cart/items/{item_id}",
        json={"quantity": 4},
        headers=headers,
    )
    assert res.status_code == 200
    cart = res.get_json()["cart"]
    assert cart["items"][0]["quantity"] == 4
    assert cart["items"][0]["line_total"] == "1000.00"
    assert cart["subtotal"] == "1000.00"


def test_remove_cart_item(client, setup_catalog):
    user, headers = as_customer(client, "remove_item_user@example.com")
    add_res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m1"].id, "quantity": 1},
        headers=headers,
    )
    item_id = add_res.get_json()["cart"]["items"][0]["id"]

    del_res = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert del_res.status_code == 200
    cart = del_res.get_json()["cart"]
    assert cart["is_empty"] is True
    assert cart["items"] == []


def test_clear_cart_preserves_cart_row(client, setup_catalog):
    user, headers = as_customer(client, "clear_cart_user@example.com")
    client.post("/api/cart/items", json={"meal_id": setup_catalog["m1"].id, "quantity": 1}, headers=headers)
    client.post("/api/cart/items", json={"meal_id": setup_catalog["m2"].id, "quantity": 2}, headers=headers)

    res = client.delete("/api/cart", headers=headers)
    assert res.status_code == 200
    cart = res.get_json()["cart"]
    assert cart["is_empty"] is True

    # Verify Cart table row still exists for the user
    cart_row = Cart.query.filter_by(user_id=user.id).first()
    assert cart_row is not None
    assert CartItem.query.filter_by(cart_id=cart_row.id).count() == 0


def test_customer_cannot_modify_another_users_cart(client, setup_catalog):
    user_a, headers_a = as_customer(client, "user_a@example.com")
    add_res = client.post(
        "/api/cart/items",
        json={"meal_id": setup_catalog["m1"].id, "quantity": 1},
        headers=headers_a,
    )
    item_id = add_res.get_json()["cart"]["items"][0]["id"]

    # Customer B tries to update or delete Customer A's item
    user_b, headers_b = as_customer(client, "user_b@example.com")
    patch_res = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 5}, headers=headers_b)
    assert patch_res.status_code == 404

    delete_res = client.delete(f"/api/cart/items/{item_id}", headers=headers_b)
    assert delete_res.status_code == 404


def test_food_memory_records_added_to_cart_event(client, setup_catalog):
    user, headers = as_customer(client, "fm_cart_user@example.com")
    meal = setup_catalog["m1"]

    client.post("/api/cart/items", json={"meal_id": meal.id, "quantity": 2}, headers=headers)
    event = FoodMemory.query.filter_by(user_id=user.id, event_type="added_to_cart").first()
    assert event is not None
    assert event.meal_id == meal.id
    assert event.restaurant_id == meal.restaurant_id
    assert event.event_data["quantity"] == 2
