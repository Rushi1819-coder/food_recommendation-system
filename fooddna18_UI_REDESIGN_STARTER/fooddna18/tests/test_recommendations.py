"""Phase 5: scoring, filtering, recommendation API and history.

WRITTEN BUT NOT YET EXECUTED (the project owner runs the full suite in the
dedicated testing phase). Expectations may contain mistakes.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import FoodMemory, Recommendation, UserPreference
from app.services import recommendation_service as svc
from tests.conftest import csrf_headers, login, make_user
from tests.test_browsing import add_category, add_meal, add_restaurant


# ======================================================================
# Pure scoring tests (no HTTP; plain objects stand in for meals)
# ======================================================================

def meal(id, name, price, **overrides):
    values = dict(
        cuisine="North Indian", meal_type="Dinner", taste="Savory",
        spice_level="Mild", portion_size="Regular",
        dietary_preference="Vegetarian", food_type="Veg",
    )
    values.update(overrides)
    return SimpleNamespace(id=id, name=name, price=Decimal(price), **values)


def profile(**values):
    return svc.PreferenceProfile(values)


def rows(*meals):
    return [(m, None, None) for m in meals]


def test_no_preferences_scores_nothing():
    assert svc.score_meal(profile(), meal(1, "A", "100")) is None


def test_matching_is_case_insensitive_and_scores_100():
    result = svc.score_meal(
        profile(cuisine="north indian", taste="SAVORY"), meal(1, "A", "100")
    )
    assert result["score"] == Decimal("100.00")
    assert set(result["matched"]) == {"cuisine", "taste"}


def test_score_is_share_of_available_points():
    # taste (15) matches, cuisine (20) does not: 15 / 35 = 42.86
    result = svc.score_meal(
        profile(cuisine="Italian", taste="Savory"), meal(1, "A", "100")
    )
    assert result["score"] == Decimal("42.86")


def test_meal_that_earns_no_points_is_not_recommended():
    assert svc.score_meal(profile(cuisine="Italian"), meal(1, "A", "100")) is None


def test_spice_one_step_away_earns_half_credit():
    result = svc.score_meal(profile(spice_level="Medium"), meal(1, "A", "100"))
    assert result["score"] == Decimal("50.00")
    assert result["partial"] == ["spice_level"]
    assert svc.score_meal(profile(spice_level="Hot"), meal(1, "A", "100")) is None
    assert svc.score_meal(profile(spice_level="Volcanic"), meal(1, "A", "100")) is None


def test_budget_is_a_hard_limit_and_equal_price_is_allowed():
    assert svc.failed_hard_rule(profile(budget="200"), meal(1, "A", "240")) == "budget"
    assert svc.failed_hard_rule(profile(budget="240"), meal(1, "A", "240")) is None


def test_veg_and_vegan_are_hard_but_non_veg_is_only_a_taste():
    non_veg = meal(2, "B", "100", food_type="Non-Veg")
    vegan = meal(3, "C", "100", food_type="Vegan")
    assert svc.failed_hard_rule(profile(food_type="Veg"), non_veg) == "food_type"
    assert svc.failed_hard_rule(profile(food_type="Veg"), vegan) is None
    assert svc.failed_hard_rule(profile(food_type="Vegan"), meal(1, "A", "1")) == "food_type"
    assert svc.failed_hard_rule(profile(food_type="Non-Veg"), meal(1, "A", "1")) is None


def test_dietary_preference_rules():
    plain = meal(1, "A", "100", dietary_preference=None)
    vegan = meal(2, "B", "100", dietary_preference="Vegan")
    veg = meal(3, "C", "100", dietary_preference="Vegetarian")
    gf = meal(4, "D", "100", dietary_preference="Gluten-Free")
    assert svc.failed_hard_rule(profile(dietary_preference="Vegan"), plain) == "dietary_preference"
    assert svc.failed_hard_rule(profile(dietary_preference="Vegan"), veg) == "dietary_preference"
    assert svc.failed_hard_rule(profile(dietary_preference="Vegetarian"), vegan) is None
    assert svc.failed_hard_rule(profile(dietary_preference="gluten-free"), gf) is None


def test_ranking_order_limit_and_tie_break():
    meals = [
        meal(1, "B", "300", cuisine="Italian"),
        meal(2, "A", "200"),
        meal(3, "C", "100"),
        meal(4, "D", "50", cuisine="Chinese", food_type="Non-Veg"),
    ]
    ranked, stats = svc.rank_meals(
        profile(cuisine="North Indian", budget="250", food_type="Veg"),
        rows(*meals), 10,
    )
    # C and A both score 100; the cheaper one is listed first.
    assert [r[0].name for r in ranked] == ["C", "A"]
    assert stats["excluded"] == {"budget": 1, "food_type": 1, "dietary_preference": 0}
    assert len(svc.rank_meals(profile(cuisine="North Indian"), rows(*meals), 1)[0]) == 1


def test_only_hard_preferences_still_give_results():
    ranked, _ = svc.rank_meals(
        profile(budget="150"), rows(meal(1, "A", "100"), meal(2, "B", "200")), 5
    )
    assert [r[0].name for r in ranked] == ["A"]
    assert ranked[0][3]["score"] == Decimal("100.00")


# ======================================================================
# API tests
# ======================================================================

@pytest.fixture()
def catalog(app):
    garden = add_restaurant("Garden")
    wok = add_restaurant("Wok")
    pending = add_restaurant("Pending Kitchen", status="pending")
    mains = add_category("Mains")
    retired = add_category("Retired", active=False)

    data = {"garden": garden, "wok": wok, "mains": mains}
    data["paneer"] = add_meal(
        garden, mains, "Paneer Tikka", "240.00", taste="Savory",
        spice_level="Mild",
    )
    data["biryani"] = add_meal(
        garden, mains, "Chicken Biryani", "310.00", taste="Spicy",
        spice_level="Hot", food_type="Non-Veg", dietary_preference=None,
    )
    data["noodles"] = add_meal(
        wok, mains, "Hakka Noodles", "160.50", cuisine="Chinese",
        taste="Tangy", food_type="Vegan", dietary_preference="Vegan",
    )
    # Hidden by the Phase 4 rules; each one matches North Indian / Dinner
    # exactly, so only the visibility rules can keep it out.
    data["soldout"] = add_meal(garden, mains, "Sold Out Curry", "100.00", is_available=False)
    data["retired"] = add_meal(wok, retired, "Retired Sundae", "90.00")
    data["hidden"] = add_meal(pending, mains, "Pending Thali", "199.00")
    db.session.commit()
    return data


def customer(client, email="cust@example.com", prefs=None):
    user = make_user(email)
    if prefs is not None:
        db.session.add(UserPreference(user_id=user.id, **prefs))
        db.session.commit()
    assert login(client, email).status_code == 200
    return user


def names(response):
    return [r["meal"]["name"] for r in response.get_json()["recommendations"]]


BASE_PREFS = dict(cuisine="North Indian", meal_type="Dinner", taste="Savory")


# ----- access --------------------------------------------------------------

def test_recommendation_endpoints_require_login(client, catalog):
    assert client.get("/api/recommendations").status_code == 401
    assert client.post("/api/recommendations").status_code == 401
    assert client.get("/api/recommendations/history").status_code == 401
    assert client.post("/api/recommendations/1/select").status_code == 401


def test_non_customers_are_refused(client, catalog):
    make_user("admin@example.com", role="super_admin")
    assert login(client, "admin@example.com", role="super_admin").status_code == 200
    assert client.get("/api/recommendations").status_code == 403
    assert client.get("/api/recommendations/history").status_code == 403


def test_post_requires_csrf(client, catalog):
    customer(client, prefs=BASE_PREFS)
    assert client.post("/api/recommendations").status_code == 403
    assert Recommendation.query.count() == 0


# ----- ranking and explanations -------------------------------------------

def test_ranked_by_score_with_explanations(client, catalog):
    customer(client, prefs=BASE_PREFS)
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    body = response.get_json()
    assert body["has_preferences"] is True
    assert names(response) == ["Paneer Tikka", "Chicken Biryani", "Hakka Noodles"]
    scores = [r["score"] for r in body["recommendations"]]
    # paneer: 50/50, biryani: cuisine+meal_type 35/50, noodles: meal_type 15/50
    assert scores == ["100.00", "70.00", "30.00"]
    first = body["recommendations"][0]
    assert first["rank"] == 1
    assert set(first["matched"]) == {"cuisine", "meal_type", "taste"}
    assert any("Cuisine" in text for text in first["reasons"])
    assert first["meal"]["restaurant"]["name"] == "Garden"


def test_limit_is_configurable_and_validated(client, catalog):
    customer(client, prefs=BASE_PREFS)
    assert len(names(client.get("/api/recommendations?limit=1"))) == 1
    assert client.get("/api/recommendations").get_json()["summary"]["limit"] == 10
    for bad in ("0", "-1", "abc", "31", "1.5", "1e1"):
        assert client.get(f"/api/recommendations?limit={bad}").status_code == 400, bad


def test_hidden_meals_are_never_recommended(client, catalog):
    customer(client, prefs=BASE_PREFS)
    shown = names(client.get("/api/recommendations?limit=30"))
    for hidden in ("Sold Out Curry", "Retired Sundae", "Pending Thali"):
        assert hidden not in shown


def test_unavailable_meal_disappears_when_it_sells_out(client, catalog):
    customer(client, prefs=BASE_PREFS)
    assert "Paneer Tikka" in names(client.get("/api/recommendations"))
    catalog["paneer"].is_available = False
    db.session.commit()
    assert "Paneer Tikka" not in names(client.get("/api/recommendations"))


def test_meals_of_a_restaurant_that_loses_approval_disappear(client, catalog):
    customer(client, prefs=BASE_PREFS)
    catalog["garden"].status = "rejected"
    db.session.commit()
    shown = names(client.get("/api/recommendations"))
    assert "Paneer Tikka" not in shown and "Chicken Biryani" not in shown


# ----- hard filters --------------------------------------------------------

def test_budget_filter(client, catalog):
    customer(client, prefs=dict(BASE_PREFS, budget=Decimal("200.00")))
    response = client.get("/api/recommendations")
    assert names(response) == ["Hakka Noodles"]
    assert response.get_json()["summary"]["excluded"]["budget"] == 2


def test_budget_equal_to_price_is_allowed(client, catalog):
    customer(client, prefs=dict(BASE_PREFS, budget=Decimal("240.00")))
    assert "Paneer Tikka" in names(client.get("/api/recommendations"))


def test_dietary_preference_filter(client, catalog):
    customer(client, prefs=dict(dietary_preference="Vegan"))
    assert names(client.get("/api/recommendations")) == ["Hakka Noodles"]


def test_vegetarian_dietary_preference_accepts_vegan_dishes(client, catalog):
    customer(client, prefs=dict(dietary_preference="Vegetarian"))
    assert sorted(names(client.get("/api/recommendations"))) == [
        "Hakka Noodles", "Paneer Tikka"
    ]


def test_veg_food_type_hides_non_veg(client, catalog):
    customer(client, prefs=dict(cuisine="North Indian", food_type="Veg"))
    shown = names(client.get("/api/recommendations"))
    assert "Chicken Biryani" not in shown and "Paneer Tikka" in shown


def test_non_veg_preference_does_not_hide_veg_dishes(client, catalog):
    customer(client, prefs=dict(cuisine="North Indian", food_type="Non-Veg"))
    shown = names(client.get("/api/recommendations"))
    assert shown[0] == "Chicken Biryani"  # cuisine + food type
    assert "Paneer Tikka" in shown


# ----- customers without usable data ---------------------------------------

def test_customer_without_preferences(client, catalog):
    customer(client)
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    body = response.get_json()
    assert body["has_preferences"] is False
    assert body["recommendations"] == []
    assert "preferences" in body["message"].lower()


def test_saved_but_all_blank_preferences_count_as_none(client, catalog):
    customer(client, prefs={})
    assert client.get("/api/recommendations").get_json()["has_preferences"] is False


def test_nothing_matches(client, catalog):
    customer(client, prefs=dict(cuisine="Mexican"))
    body = client.get("/api/recommendations").get_json()
    assert body["recommendations"] == []
    assert body["message"]
    assert body["summary"]["no_match"] == 3


def test_everything_excluded_by_restrictions(client, catalog):
    customer(client, prefs=dict(budget=Decimal("1.00")))
    body = client.get("/api/recommendations").get_json()
    assert body["recommendations"] == []
    assert "budget" in body["message"].lower()


def test_empty_catalogue(client, app):
    customer(client, prefs=BASE_PREFS)
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    assert response.get_json()["recommendations"] == []


# ----- using the authenticated user only -----------------------------------

def test_user_id_in_query_or_body_is_ignored(client, catalog):
    other = make_user("other@example.com")
    db.session.add(UserPreference(user_id=other.id, cuisine="Chinese"))
    db.session.commit()
    customer(client, prefs=BASE_PREFS)

    assert names(client.get(f"/api/recommendations?user_id={other.id}"))[0] == "Paneer Tikka"
    posted = client.post(
        "/api/recommendations",
        json={"user_id": other.id, "limit": 3},
        headers=csrf_headers(client),
    )
    assert posted.status_code == 200
    assert Recommendation.query.filter_by(user_id=other.id).count() == 0


# ----- recording history ---------------------------------------------------

def test_get_does_not_write_anything(client, catalog):
    customer(client, prefs=BASE_PREFS)
    client.get("/api/recommendations")
    assert Recommendation.query.count() == 0
    assert FoodMemory.query.count() == 0


def test_post_records_history(client, catalog):
    user = customer(client, prefs=BASE_PREFS)
    response = client.post(
        "/api/recommendations", json={"limit": 2}, headers=csrf_headers(client)
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["history"] == {"created": 2, "updated": 0}
    rows = Recommendation.query.filter_by(user_id=user.id).order_by(Recommendation.id).all()
    assert [r.meal_id for r in rows] == [
        body["recommendations"][0]["meal"]["id"],
        body["recommendations"][1]["meal"]["id"],
    ]
    assert rows[0].score == Decimal("100.00")
    assert "Cuisine" in rows[0].reason


def test_repeating_within_the_window_updates_instead_of_duplicating(client, catalog):
    user = customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    client.post("/api/recommendations", headers=headers)
    count = Recommendation.query.filter_by(user_id=user.id).count()
    second = client.post("/api/recommendations", headers=headers).get_json()
    assert Recommendation.query.filter_by(user_id=user.id).count() == count
    assert second["history"]["created"] == 0 and second["history"]["updated"] == count


def test_after_the_window_a_new_history_row_is_added(client, catalog):
    user = customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    client.post("/api/recommendations", headers=headers)
    old = datetime.utcnow() - timedelta(minutes=svc.RECOMMENDATION_DEDUPE_MINUTES + 5)
    Recommendation.query.update({"generated_at": old})
    db.session.commit()
    client.post("/api/recommendations", headers=headers)
    assert Recommendation.query.filter_by(user_id=user.id).count() == 6


def test_nothing_is_recorded_when_there_is_nothing_to_recommend(client, catalog):
    customer(client)
    response = client.post("/api/recommendations", headers=csrf_headers(client))
    assert response.status_code == 200
    assert Recommendation.query.count() == 0
    assert FoodMemory.query.count() == 0


def test_post_rejects_bad_limit_and_bad_body(client, catalog):
    customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    assert client.post("/api/recommendations", json={"limit": 99}, headers=headers).status_code == 400
    assert client.post("/api/recommendations", json={"limit": "x"}, headers=headers).status_code == 400
    assert client.post("/api/recommendations", json={"limit": True}, headers=headers).status_code == 400
    assert client.post("/api/recommendations", json=[1], headers=headers).status_code == 400


def test_post_records_a_food_memory_event_once(client, catalog):
    user = customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    client.post("/api/recommendations", headers=headers)
    client.post("/api/recommendations", headers=headers)
    events = FoodMemory.query.filter_by(user_id=user.id, event_type="recommendations_viewed").all()
    assert len(events) == 1
    assert events[0].meal_id is None
    assert events[0].event_data["returned"] == 3


# ----- history endpoint ----------------------------------------------------

def test_history_lists_only_the_users_own_rows(client, catalog):
    other = make_user("other@example.com")
    db.session.add(Recommendation(
        user_id=other.id, meal_id=catalog["paneer"].id, score=Decimal("90"), reason="x"
    ))
    db.session.commit()
    user = customer(client, prefs=BASE_PREFS)
    client.post("/api/recommendations", headers=csrf_headers(client))

    body = client.get("/api/recommendations/history").get_json()
    assert body["pagination"]["total"] == 3
    assert {h["id"] for h in body["history"]} == {
        r.id for r in Recommendation.query.filter_by(user_id=user.id)
    }
    first = body["history"][0]
    assert first["meal"]["restaurant_name"] and first["currently_available"] is True


def test_history_pagination_and_availability_flag(client, catalog):
    customer(client, prefs=BASE_PREFS)
    client.post("/api/recommendations", headers=csrf_headers(client))
    page = client.get("/api/recommendations/history?page=1&page_size=2").get_json()
    assert len(page["history"]) == 2
    assert page["pagination"] == {"page": 1, "page_size": 2, "total": 3, "total_pages": 2}

    catalog["paneer"].is_available = False
    db.session.commit()
    everything = client.get("/api/recommendations/history?page_size=50").get_json()["history"]
    flags = {h["meal"]["name"]: h["currently_available"] for h in everything}
    assert flags["Paneer Tikka"] is False and flags["Hakka Noodles"] is True


def test_history_rejects_bad_paging(client, catalog):
    customer(client, prefs=BASE_PREFS)
    for query in ("page=0", "page_size=51", "page=abc"):
        assert client.get(f"/api/recommendations/history?{query}").status_code == 400


# ----- selecting a recommendation -----------------------------------------

def test_select_a_recommended_meal_records_food_memory(client, catalog):
    user = customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    client.post("/api/recommendations", headers=headers)
    meal_id = catalog["paneer"].id
    response = client.post(f"/api/recommendations/{meal_id}/select", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["recorded"] is True
    event = FoodMemory.query.filter_by(user_id=user.id, event_type="recommendation_selected").one()
    assert event.meal_id == meal_id and event.restaurant_id == catalog["garden"].id


def test_select_refuses_meals_that_were_not_recommended_to_you(client, catalog):
    other = make_user("other@example.com")
    db.session.add(Recommendation(
        user_id=other.id, meal_id=catalog["paneer"].id, score=Decimal("90"), reason="x"
    ))
    db.session.commit()
    customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    response = client.post(f"/api/recommendations/{catalog['paneer'].id}/select", headers=headers)
    assert response.status_code == 404
    assert FoodMemory.query.count() == 0


def test_select_validates_id_csrf_and_visibility(client, catalog):
    customer(client, prefs=BASE_PREFS)
    headers = csrf_headers(client)
    client.post("/api/recommendations", headers=headers)
    meal_id = catalog["paneer"].id
    assert client.post(f"/api/recommendations/{meal_id}/select").status_code == 403
    for bad in ("abc", "0", "-1", "1.5"):
        assert client.post(f"/api/recommendations/{bad}/select", headers=headers).status_code == 400
    catalog["paneer"].is_available = False
    db.session.commit()
    assert client.post(f"/api/recommendations/{meal_id}/select", headers=headers).status_code == 404
