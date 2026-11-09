"""Phase 5: Food Memory service and meal-view API.

WRITTEN BUT NOT YET EXECUTED (the project owner runs the full suite in the
dedicated testing phase). Expectations may contain mistakes.
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import FoodMemory
from app.services import food_memory_service as memory
from tests.conftest import csrf_headers, login, make_user
from tests.test_browsing import add_category, add_meal, add_restaurant


@pytest.fixture()
def dish(app):
    restaurant = add_restaurant("Garden")
    category = add_category("Mains")
    meal = add_meal(restaurant, category, "Paneer Tikka", "240.00")
    hidden = add_meal(restaurant, category, "Sold Out", "10.00", is_available=False)
    db.session.commit()
    return {"restaurant": restaurant, "meal": meal, "hidden": hidden}


def signed_in(client, email="cust@example.com"):
    user = make_user(email)
    assert login(client, email).status_code == 200
    return user, csrf_headers(client)


# ----- service -------------------------------------------------------------

def test_record_event_stores_ids_and_data(app, dish):
    user = make_user("a@example.com")
    row = memory.record_event(
        user.id, "recommendation_selected", meal_id=dish["meal"].id,
        restaurant_id=dish["restaurant"].id, data={"source": "test", "n": 2},
    )
    stored = FoodMemory.query.one()
    assert stored.id == row.id
    assert stored.event_data == {"source": "test", "n": 2}
    assert stored.restaurant_id == dish["restaurant"].id


def test_unknown_event_types_and_bad_data_are_refused(app, dish):
    user = make_user("a@example.com")
    with pytest.raises(ValueError):
        memory.record_event(user.id, "made_up_event")
    with pytest.raises(ValueError):
        memory.record_event(user.id, "meal_viewed", data={"nested": {"a": 1}})
    with pytest.raises(ValueError):
        memory.record_event(user.id, "meal_viewed", data={"k": "x" * 101})
    with pytest.raises(ValueError):
        memory.record_event(user.id, "meal_viewed", data={f"k{i}": i for i in range(7)})
    assert FoodMemory.query.count() == 0


def test_duplicate_views_inside_the_window_are_skipped(app, dish):
    user = make_user("a@example.com")
    start = datetime.utcnow()
    assert memory.record_event(user.id, "meal_viewed", meal_id=dish["meal"].id, now=start)
    assert memory.record_event(user.id, "meal_viewed", meal_id=dish["meal"].id, now=start) is None
    later = start + timedelta(minutes=memory.EVENT_TYPES["meal_viewed"] + 1)
    assert memory.record_event(user.id, "meal_viewed", meal_id=dish["meal"].id, now=later)
    assert FoodMemory.query.count() == 2


def test_dedupe_is_per_user(app, dish):
    a, b = make_user("a@example.com"), make_user("b@example.com")
    assert memory.record_event(a.id, "meal_viewed", meal_id=dish["meal"].id)
    assert memory.record_event(b.id, "meal_viewed", meal_id=dish["meal"].id)


def test_events_without_a_dedupe_window_are_always_stored(app, dish):
    user = make_user("a@example.com")
    for _ in range(2):
        assert memory.record_event(user.id, "recommendation_selected", meal_id=dish["meal"].id)
    assert FoodMemory.query.count() == 2


def test_commit_false_leaves_the_transaction_to_the_caller(app, dish):
    user = make_user("a@example.com")
    memory.record_event(user.id, "meal_viewed", meal_id=dish["meal"].id, commit=False)
    db.session.rollback()
    assert FoodMemory.query.count() == 0


# ----- meal-view API -------------------------------------------------------

def test_meal_view_requires_login_and_csrf(client, dish):
    body = {"meal_id": dish["meal"].id}
    assert client.post("/api/food-memory/meal-views", json=body).status_code == 401
    signed_in(client)
    assert client.post("/api/food-memory/meal-views", json=body).status_code == 403


def test_non_customers_cannot_record_views(client, dish):
    make_user("admin@example.com", role="super_admin")
    login(client, "admin@example.com", role="super_admin")
    response = client.post(
        "/api/food-memory/meal-views",
        json={"meal_id": dish["meal"].id}, headers=csrf_headers(client),
    )
    assert response.status_code == 403
    assert FoodMemory.query.count() == 0


def test_meal_view_is_recorded_once_per_window(client, dish):
    user, headers = signed_in(client)
    body = {"meal_id": dish["meal"].id}
    first = client.post("/api/food-memory/meal-views", json=body, headers=headers)
    second = client.post("/api/food-memory/meal-views", json=body, headers=headers)
    assert first.get_json()["recorded"] is True
    assert second.get_json()["recorded"] is False
    row = FoodMemory.query.filter_by(user_id=user.id).one()
    assert row.event_type == "meal_viewed"
    assert row.meal_id == dish["meal"].id
    assert row.restaurant_id == dish["restaurant"].id


def test_meal_view_rejects_hidden_unknown_and_malformed(client, dish):
    user, headers = signed_in(client)
    url = "/api/food-memory/meal-views"
    assert client.post(url, json={"meal_id": dish["hidden"].id}, headers=headers).status_code == 404
    assert client.post(url, json={"meal_id": 999999}, headers=headers).status_code == 404
    for bad in ({"meal_id": "abc"}, {"meal_id": 0}, {"meal_id": True},
                {"meal_id": [1]}, {"meal_id": None}, {}):
        assert client.post(url, json=bad, headers=headers).status_code == 400, bad
    assert client.post(url, json=[1], headers=headers).status_code == 400
    assert FoodMemory.query.count() == 0


def test_user_id_in_the_body_is_ignored(client, dish):
    victim = make_user("victim@example.com")
    attacker, headers = signed_in(client, "attacker@example.com")
    client.post(
        "/api/food-memory/meal-views",
        json={"meal_id": dish["meal"].id, "user_id": victim.id}, headers=headers,
    )
    assert FoodMemory.query.filter_by(user_id=victim.id).count() == 0
    assert FoodMemory.query.filter_by(user_id=attacker.id).count() == 1
