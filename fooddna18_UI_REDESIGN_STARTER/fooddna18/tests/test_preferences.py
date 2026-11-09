"""Phase 5: customer food preferences API.

WRITTEN BUT NOT YET EXECUTED (the project owner runs the full suite in the
dedicated testing phase). Expectations may contain mistakes.
"""

from decimal import Decimal

import pytest

from app.extensions import db
from app.models import UserPreference
from tests.conftest import csrf_headers, login, make_user

FULL = {
    "cuisine": "North Indian",
    "meal_type": "Dinner",
    "taste": "Savory",
    "spice_level": "Medium",
    "portion_size": "Regular",
    "food_type": "Veg",
    "dietary_preference": "Vegetarian",
    "budget": "300",
}


def as_customer(client, email="cust@example.com"):
    user = make_user(email)
    assert login(client, email).status_code == 200
    return user, csrf_headers(client)


def put(client, headers, payload):
    return client.put("/api/preferences", json=payload, headers=headers)


# ----- authentication and roles --------------------------------------------

def test_preferences_require_login(client, app):
    assert client.get("/api/preferences").status_code == 401
    assert client.put("/api/preferences", json=FULL).status_code == 401


def test_put_requires_csrf_token(client, app):
    as_customer(client)
    assert client.put("/api/preferences", json=FULL).status_code == 403
    bad = client.put(
        "/api/preferences", json=FULL, headers={"X-CSRF-Token": "nope"}
    )
    assert bad.status_code == 403
    assert UserPreference.query.count() == 0


@pytest.mark.parametrize("role", ["super_admin", "restaurant_admin"])
def test_non_customers_are_refused(client, app, role):
    make_user(
        f"{role}@example.com", role=role, approval_status="approved"
    )
    assert login(client, f"{role}@example.com", role=role).status_code == 200
    headers = csrf_headers(client)
    assert client.get("/api/preferences").status_code == 403
    assert put(client, headers, FULL).status_code == 403
    assert UserPreference.query.count() == 0


# ----- read, create, update ------------------------------------------------

def test_get_before_anything_is_saved(client, app):
    as_customer(client)
    body = client.get("/api/preferences").get_json()
    assert body["success"] is True
    assert body["preferences"] is None
    assert body["has_preferences"] is False


def test_create_preferences(client, app):
    user, headers = as_customer(client)
    response = put(client, headers, FULL)
    assert response.status_code == 201
    body = response.get_json()
    assert body["created"] is True
    assert body["preferences"]["cuisine"] == "North Indian"
    assert body["preferences"]["budget"] == "300.00"

    row = UserPreference.query.filter_by(user_id=user.id).one()
    assert row.cuisine == "North Indian"
    assert row.budget == Decimal("300.00")

    fetched = client.get("/api/preferences").get_json()
    assert fetched["has_preferences"] is True
    assert fetched["preferences"]["spice_level"] == "Medium"


def test_update_preferences_keeps_a_single_row(client, app):
    user, headers = as_customer(client)
    assert put(client, headers, FULL).status_code == 201

    changed = dict(FULL, cuisine="Chinese", budget="199.50")
    response = put(client, headers, changed)
    assert response.status_code == 200
    assert response.get_json()["created"] is False

    assert UserPreference.query.filter_by(user_id=user.id).count() == 1
    row = UserPreference.query.filter_by(user_id=user.id).one()
    assert row.cuisine == "Chinese"
    assert row.budget == Decimal("199.50")


def test_saving_many_times_never_duplicates(client, app):
    user, headers = as_customer(client)
    for _ in range(4):
        assert put(client, headers, FULL).status_code in (200, 201)
    assert UserPreference.query.filter_by(user_id=user.id).count() == 1


def test_blank_and_missing_fields_clear_the_preference(client, app):
    user, headers = as_customer(client)
    put(client, headers, FULL)
    response = put(client, headers, {"cuisine": "  ", "budget": "", "taste": None})
    assert response.status_code == 200
    row = UserPreference.query.filter_by(user_id=user.id).one()
    assert row.cuisine is None and row.budget is None and row.taste is None
    # Fields that were not sent are cleared too (PUT replaces everything).
    assert row.meal_type is None and row.dietary_preference is None
    assert client.get("/api/preferences").get_json()["has_preferences"] is False


def test_values_are_trimmed(client, app):
    user, headers = as_customer(client)
    put(client, headers, {"cuisine": "  Italian  "})
    assert UserPreference.query.one().cuisine == "Italian"


def test_numeric_budget_is_accepted(client, app):
    user, headers = as_customer(client)
    assert put(client, headers, {"budget": 250}).status_code == 201
    assert UserPreference.query.one().budget == Decimal("250.00")


# ----- validation ----------------------------------------------------------

@pytest.mark.parametrize(
    "payload, field",
    [
        ({"budget": "0"}, "budget"),
        ({"budget": "-5"}, "budget"),
        ({"budget": "abc"}, "budget"),
        ({"budget": "1e3"}, "budget"),
        ({"budget": "12.345"}, "budget"),
        ({"budget": "99999999"}, "budget"),
        ({"budget": True}, "budget"),
        ({"budget": [100]}, "budget"),
        ({"cuisine": "x" * 81}, "cuisine"),
        ({"spice_level": "y" * 31}, "spice_level"),
        ({"cuisine": "<script>alert(1)</script>"}, "cuisine"),
        ({"taste": "tab\there"}, "taste"),
        ({"meal_type": 5}, "meal_type"),
        ({"food_type": ["Veg"]}, "food_type"),
        ({"dietary_preference": {"a": 1}}, "dietary_preference"),
    ],
)
def test_invalid_values_are_rejected(client, app, payload, field):
    as_customer(client)
    response = put(client, csrf_headers(client), payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert field in body["errors"]
    assert UserPreference.query.count() == 0


@pytest.mark.parametrize("body", [[], "text", 5, None])
def test_non_object_body_is_rejected_and_never_wipes_preferences(client, app, body):
    user, headers = as_customer(client)
    put(client, headers, FULL)
    response = client.put("/api/preferences", json=body, headers=headers)
    assert response.status_code == 400
    assert UserPreference.query.filter_by(user_id=user.id).one().cuisine == "North Indian"


def test_empty_request_body_is_rejected(client, app):
    user, headers = as_customer(client)
    put(client, headers, FULL)
    response = client.put("/api/preferences", headers=headers)
    assert response.status_code == 400
    assert UserPreference.query.one().cuisine == "North Indian"


def test_sql_injection_text_is_rejected_or_harmless(client, app):
    as_customer(client)
    response = put(client, csrf_headers(client), {"cuisine": "x'; DROP TABLE users;--"})
    # ';' is not an allowed character, so this is a clean 400.
    assert response.status_code == 400
    assert make_user("still-here@example.com").id


# ----- one customer cannot touch another's preferences ---------------------

def test_user_id_in_the_payload_is_ignored(client, app):
    victim = make_user("victim@example.com")
    db.session.add(UserPreference(user_id=victim.id, cuisine="Italian"))
    db.session.commit()

    attacker, headers = as_customer(client, "attacker@example.com")
    response = put(client, headers, dict(FULL, user_id=victim.id))
    assert response.status_code == 201

    assert UserPreference.query.filter_by(user_id=victim.id).one().cuisine == "Italian"
    assert UserPreference.query.filter_by(user_id=attacker.id).one().cuisine == "North Indian"


def test_each_customer_only_sees_their_own_preferences(client, app):
    a = make_user("a@example.com")
    b = make_user("b@example.com")
    db.session.add_all([
        UserPreference(user_id=a.id, cuisine="Italian"),
        UserPreference(user_id=b.id, cuisine="Mexican"),
    ])
    db.session.commit()

    assert login(client, "a@example.com").status_code == 200
    assert client.get("/api/preferences").get_json()["preferences"]["cuisine"] == "Italian"
    # A query-string user id changes nothing.
    other = client.get(f"/api/preferences?user_id={b.id}").get_json()
    assert other["preferences"]["cuisine"] == "Italian"


def test_no_route_addresses_another_users_preferences(client, app):
    as_customer(client)
    for url in ("/api/preferences/1", "/api/users/1/preferences"):
        assert client.get(url).status_code == 404


def test_response_never_contains_other_users_or_secrets(client, app):
    user, headers = as_customer(client)
    body = put(client, headers, FULL).get_json()
    text = str(body).lower()
    assert "password" not in text and "hash" not in text and "token" not in text


# ----- filter options used by the form -------------------------------------

def test_filter_options_include_taste_and_portion(client, app):
    from tests.test_browsing import add_category, add_meal, add_restaurant

    restaurant = add_restaurant("Garden")
    category = add_category("Mains")
    add_meal(restaurant, category, "Paneer", "240.00")
    db.session.commit()
    options = client.get("/api/meals/filters").get_json()["filters"]
    assert options["tastes"] == ["Savory"]
    assert options["portion_sizes"] == ["Regular"]
