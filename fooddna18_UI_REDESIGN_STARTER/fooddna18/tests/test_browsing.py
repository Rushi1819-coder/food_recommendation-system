"""Phase 4: public restaurant, category and meal browsing APIs.

Every test runs against the real test database (fooddna_test) through the
real Flask app; nothing is mocked.
"""

from decimal import Decimal

import pytest

from app.extensions import db
from app.models import FoodCategory, Meal, Restaurant


def add_restaurant(name, status="approved"):
    row = Restaurant(
        name=name,
        description=f"{name} description",
        address=f"{name} address",
        phone="555-0100",
        status=status,
    )
    db.session.add(row)
    db.session.flush()
    return row


def add_category(name, active=True):
    row = FoodCategory(name=name, description=name, is_active=active)
    db.session.add(row)
    db.session.flush()
    return row


def add_meal(restaurant, category, name, price, **overrides):
    values = dict(
        description=f"{name} description",
        cuisine="North Indian",
        meal_type="Dinner",
        taste="Savory",
        spice_level="Mild",
        portion_size="Regular",
        dietary_preference="Vegetarian",
        food_type="Veg",
        image_url=None,
        is_available=True,
    )
    values.update(overrides)
    row = Meal(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name=name,
        price=Decimal(price),
        **values,
    )
    db.session.add(row)
    db.session.flush()
    return row


@pytest.fixture()
def catalog(app):
    """A small catalogue with visible AND hidden rows."""
    garden = add_restaurant("Garden")
    wok = add_restaurant("Wok")
    pending = add_restaurant("Pending Kitchen", status="pending")
    rejected = add_restaurant("Rejected Kitchen", status="rejected")

    mains = add_category("Mains")
    snacks = add_category("Snacks")
    retired = add_category("Retired", active=False)

    data = {
        "garden": garden,
        "wok": wok,
        "pending": pending,
        "rejected": rejected,
        "mains": mains,
        "snacks": snacks,
        "retired": retired,
    }
    data["paneer"] = add_meal(garden, mains, "Paneer Tikka", "240.00")
    data["biryani"] = add_meal(
        garden, mains, "Chicken Biryani", "310.00",
        food_type="Non-Veg", dietary_preference=None, spice_level="Hot",
    )
    data["noodles"] = add_meal(
        wok, snacks, "Hakka Noodles", "160.50",
        cuisine="Chinese", food_type="Vegan", dietary_preference="Vegan",
    )
    data["soldout"] = add_meal(
        garden, mains, "Sold Out Curry", "100.00", is_available=False
    )
    data["old"] = add_meal(wok, retired, "Retired Sundae", "90.00")
    data["hidden1"] = add_meal(pending, mains, "Pending Thali", "199.00")
    data["hidden2"] = add_meal(rejected, mains, "Rejected Thali", "199.00")
    data["percent"] = add_meal(
        wok, snacks, "100% Juice", "50.00", description="Pure fruit"
    )
    db.session.commit()
    return data


def names(response):
    return [m["name"] for m in response.get_json()["meals"]]


# ----- restaurants ------------------------------------------------------

def test_restaurant_list_shows_only_approved(client, catalog):
    response = client.get("/api/restaurants")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert [r["name"] for r in body["restaurants"]] == ["Garden", "Wok"]
    assert body["pagination"]["total"] == 2


def test_restaurant_meal_count_counts_only_visible_meals(client, catalog):
    body = client.get("/api/restaurants").get_json()
    counts = {r["name"]: r["meal_count"] for r in body["restaurants"]}
    # Garden: paneer + biryani (sold-out hidden). Wok: noodles + juice
    # (retired-category sundae hidden).
    assert counts == {"Garden": 2, "Wok": 2}


def test_restaurant_search_and_wildcard_escaping(client, catalog):
    body = client.get("/api/restaurants?q=gar").get_json()
    assert [r["name"] for r in body["restaurants"]] == ["Garden"]
    assert client.get("/api/restaurants?q=%25").get_json()["pagination"]["total"] == 0
    assert client.get("/api/restaurants?q=_").get_json()["pagination"]["total"] == 0


def test_restaurant_detail(client, catalog):
    response = client.get(f"/api/restaurants/{catalog['garden'].id}")
    assert response.status_code == 200
    restaurant = response.get_json()["restaurant"]
    assert restaurant["name"] == "Garden"
    assert restaurant["phone"] == "555-0100"
    assert "email" not in restaurant


@pytest.mark.parametrize("key", ["pending", "rejected"])
def test_unapproved_restaurant_detail_is_404(client, catalog, key):
    response = client.get(f"/api/restaurants/{catalog[key].id}")
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_restaurant_detail_bad_ids(client, catalog):
    assert client.get("/api/restaurants/999999").status_code == 404
    for bad in ["abc", "0", "-1", "1.5", "1e3"]:
        assert client.get(f"/api/restaurants/{bad}").status_code == 400, bad


def test_restaurant_pagination(client, catalog):
    page1 = client.get("/api/restaurants?page=1&page_size=1").get_json()
    page2 = client.get("/api/restaurants?page=2&page_size=1").get_json()
    assert page1["pagination"] == {
        "page": 1, "page_size": 1, "total": 2, "total_pages": 2
    }
    assert page1["restaurants"][0]["name"] == "Garden"
    assert page2["restaurants"][0]["name"] == "Wok"
    beyond = client.get("/api/restaurants?page=9&page_size=1").get_json()
    assert beyond["restaurants"] == []


# ----- meals: visibility -----------------------------------------------

def test_meal_list_hides_unavailable_inactive_and_unapproved(client, catalog):
    response = client.get("/api/meals?page_size=50")
    assert response.status_code == 200
    assert sorted(names(response)) == sorted(
        ["100% Juice", "Chicken Biryani", "Hakka Noodles", "Paneer Tikka"]
    )


@pytest.mark.parametrize(
    "key", ["soldout", "old", "hidden1", "hidden2"]
)
def test_hidden_meal_detail_is_404(client, catalog, key):
    assert client.get(f"/api/meals/{catalog[key].id}").status_code == 404


def test_meal_detail_shape(client, catalog):
    response = client.get(f"/api/meals/{catalog['paneer'].id}")
    assert response.status_code == 200
    meal = response.get_json()["meal"]
    assert meal["name"] == "Paneer Tikka"
    assert meal["price"] == "240.00"
    assert meal["restaurant"]["name"] == "Garden"
    assert meal["restaurant"]["address"] == "Garden address"
    assert meal["category"]["name"] == "Mains"
    assert meal["image_url"] is None


def test_meal_detail_bad_ids(client, catalog):
    assert client.get("/api/meals/999999").status_code == 404
    for bad in ["abc", "0", "-5", "1.5", "1e3"]:
        assert client.get(f"/api/meals/{bad}").status_code == 400, bad


def test_only_http_image_urls_are_returned(client, catalog):
    meal = catalog["paneer"]
    meal.image_url = "javascript:alert(1)"
    db.session.commit()
    body = client.get(f"/api/meals/{meal.id}").get_json()
    assert body["meal"]["image_url"] is None

    meal.image_url = "https://example.com/paneer.jpg"
    db.session.commit()
    body = client.get(f"/api/meals/{meal.id}").get_json()
    assert body["meal"]["image_url"] == "https://example.com/paneer.jpg"


# ----- meals: search, filters, price, sort, pagination ------------------

def test_search_by_name_and_description_case_insensitive(client, catalog):
    assert names(client.get("/api/meals?q=PANEER")) == ["Paneer Tikka"]
    assert names(client.get("/api/meals?q=fruit")) == ["100% Juice"]


def test_search_wildcards_are_literal(client, catalog):
    assert names(client.get("/api/meals?q=%25")) == ["100% Juice"]
    assert names(client.get("/api/meals?q=_")) == []


def test_search_sql_injection_text_is_harmless(client, catalog):
    response = client.get("/api/meals?q=%27%3B%20DROP%20TABLE%20meals%3B--")
    assert response.status_code == 200
    assert names(response) == []
    assert Meal.query.count() == 8


def test_filter_by_restaurant_category_cuisine_type_dietary_spice(client, catalog):
    assert sorted(names(client.get(
        f"/api/meals?restaurant_id={catalog['wok'].id}"
    ))) == ["100% Juice", "Hakka Noodles"]
    assert sorted(names(client.get(
        f"/api/meals?category_id={catalog['snacks'].id}"
    ))) == ["100% Juice", "Hakka Noodles"]
    assert names(client.get("/api/meals?cuisine=chinese")) == ["Hakka Noodles"]
    assert names(client.get("/api/meals?food_type=Non-Veg")) == ["Chicken Biryani"]
    assert names(client.get("/api/meals?dietary_preference=Vegan")) == ["Hakka Noodles"]
    assert names(client.get("/api/meals?spice_level=Hot")) == ["Chicken Biryani"]


def test_filters_combine(client, catalog):
    response = client.get(
        f"/api/meals?restaurant_id={catalog['garden'].id}&food_type=Veg"
    )
    assert names(response) == ["Paneer Tikka"]


def test_price_filters(client, catalog):
    assert sorted(names(client.get("/api/meals?min_price=200"))) == [
        "Chicken Biryani", "Paneer Tikka"
    ]
    assert sorted(names(client.get("/api/meals?max_price=160.50"))) == [
        "100% Juice", "Hakka Noodles"
    ]
    assert names(client.get("/api/meals?min_price=240&max_price=240")) == [
        "Paneer Tikka"
    ]
    assert names(client.get("/api/meals?min_price=9000")) == []


@pytest.mark.parametrize(
    "query",
    [
        "min_price=abc",
        "min_price=-1",
        "min_price=1e3",
        "min_price=1_0",
        "min_price=%2B5",
        "min_price=1.234",
        "max_price=99999999",
        "min_price=500&max_price=100",
        "page=0",
        "page=-1",
        "page=abc",
        "page_size=0",
        "page_size=51",
        "restaurant_id=abc",
        "category_id=0",
        "sort=cheapest",
        "q=" + "a" * 101,
    ],
)
def test_invalid_query_parameters_return_400(client, catalog, query):
    response = client.get(f"/api/meals?{query}")
    assert response.status_code == 400, query
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]


def test_empty_result_is_success_not_error(client, catalog):
    response = client.get("/api/meals?q=zzzznothing")
    assert response.status_code == 200
    body = response.get_json()
    assert body["meals"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["total_pages"] == 0


def test_sorting(client, catalog):
    assert names(client.get("/api/meals")) == [
        "100% Juice", "Chicken Biryani", "Hakka Noodles", "Paneer Tikka"
    ]
    assert names(client.get("/api/meals?sort=price_asc")) == [
        "100% Juice", "Hakka Noodles", "Paneer Tikka", "Chicken Biryani"
    ]
    assert names(client.get("/api/meals?sort=price_desc")) == [
        "Chicken Biryani", "Paneer Tikka", "Hakka Noodles", "100% Juice"
    ]


def test_meal_pagination(client, catalog):
    first = client.get("/api/meals?page=1&page_size=3").get_json()
    second = client.get("/api/meals?page=2&page_size=3").get_json()
    assert len(first["meals"]) == 3
    assert len(second["meals"]) == 1
    assert first["pagination"] == {
        "page": 1, "page_size": 3, "total": 4, "total_pages": 2
    }
    seen = {m["id"] for m in first["meals"]} | {m["id"] for m in second["meals"]}
    assert len(seen) == 4


# ----- categories and filter options ------------------------------------

def test_categories_list_only_active_with_counts(client, catalog):
    response = client.get("/api/categories")
    assert response.status_code == 200
    categories = {c["name"]: c["meal_count"] for c in response.get_json()["categories"]}
    assert categories == {"Mains": 2, "Snacks": 2}


def test_filter_options_come_from_visible_meals(client, catalog):
    options = client.get("/api/meals/filters").get_json()["filters"]
    assert options["cuisines"] == ["Chinese", "North Indian"]
    assert "Non-Veg" in options["food_types"]
    assert options["price_range"] == {"min": "50.00", "max": "310.00"}


def test_filter_options_with_empty_database(client, app):
    options = client.get("/api/meals/filters").get_json()["filters"]
    assert options["cuisines"] == []
    assert options["price_range"] == {"min": None, "max": None}


# ----- safety and compatibility with earlier phases ---------------------

def test_browsing_endpoints_are_read_only(client, catalog):
    for url in ("/api/restaurants", "/api/meals", "/api/categories"):
        assert client.post(url, json={}).status_code == 405
        assert client.delete(url).status_code == 405


def test_browsing_endpoints_need_no_login_but_auth_still_protected(client, catalog):
    assert client.get("/api/restaurants").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={}).status_code == 400


def test_cors_allows_configured_frontend_only(client, catalog):
    allowed = client.get(
        "/api/restaurants", headers={"Origin": "http://127.0.0.1:5500"}
    )
    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5500"
    blocked = client.get(
        "/api/restaurants", headers={"Origin": "http://evil.example"}
    )
    assert blocked.headers.get("Access-Control-Allow-Origin") is None
