import re

from flask import Blueprint, jsonify, request

from ..services import meal_service
from ..utils.query_params import (
    QueryParamError,
    parse_pagination,
    parse_positive_int,
    parse_price,
    parse_text,
)

meals_bp = Blueprint("meals", __name__, url_prefix="/api/meals")
categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")

TEXT_FILTER_NAMES = (
    "cuisine",
    "meal_type",
    "food_type",
    "dietary_preference",
    "spice_level",
)


def _bad_request(message):
    return jsonify({"success": False, "error": message}), 400


@meals_bp.get("/reverse-search")
def reverse_search():
    """
    GET /api/meals/reverse-search?q=...
    Natural language craving & preference search for Reverse Food Ordering (Screen 13).
    Parses user queries (e.g. 'spicy paneer under 300', 'healthy vegan dinner')
    and matches against visible meals.
    """
    query_text = (request.args.get("q") or "").strip().lower()
    if not query_text:
        return jsonify({"success": True, "results": [], "query": ""})

    rows = meal_service.visible_meal_rows()
    words = [w for w in re.split(r"[\s,;+]+", query_text) if len(w) >= 2]

    max_budget = None
    price_match = re.search(
        r"(?:under|below|less than|<=|<|within|budget of?)\s*(?:rs\.?|inr|₹)?\s*(\d+)",
        query_text,
    )
    if price_match:
        try:
            max_budget = float(price_match.group(1))
        except ValueError:
            max_budget = None

    scored = []
    ignored = {
        "under", "below", "less", "than", "within", "food", "want",
        "craving", "crave", "something", "need", "like", "with", "have"
    }

    for meal, restaurant, category in rows:
        score = 0
        reasons = []
        meal_price = float(meal.price)

        if max_budget is not None:
            if meal_price <= max_budget:
                score += 30
                reasons.append(f"Within budget (₹{meal_price:.0f} ≤ ₹{int(max_budget)})")
            else:
                score -= 30

        attrs = {
            "name": (meal.name or "").lower(),
            "description": (meal.description or "").lower(),
            "cuisine": (meal.cuisine or "").lower(),
            "taste": (meal.taste or "").lower(),
            "spice_level": (meal.spice_level or "").lower(),
            "food_type": (meal.food_type or "").lower(),
            "dietary": (meal.dietary_preference or "").lower(),
            "category": (category.name or "").lower(),
            "restaurant": (restaurant.name or "").lower(),
        }

        for word in words:
            if word in ignored:
                continue
            if word in attrs["name"]:
                score += 35
                reasons.append(f"Name match: {meal.name}")
            elif word in attrs["cuisine"]:
                score += 25
                reasons.append(f"Cuisine: {meal.cuisine}")
            elif word in attrs["food_type"]:
                score += 25
                reasons.append(f"{meal.food_type}")
            elif word in attrs["dietary"]:
                score += 25
                reasons.append(f"Dietary: {meal.dietary_preference}")
            elif word in attrs["taste"] or word in attrs["spice_level"]:
                score += 20
                reasons.append(f"{meal.spice_level} spice / {meal.taste}")
            elif word in attrs["category"]:
                score += 15
                reasons.append(f"Category: {category.name}")
            elif word in attrs["description"]:
                score += 10

        if score > 0:
            serialized = meal_service.serialize_meal(meal, restaurant, category)
            serialized["match_score"] = min(100, score)
            serialized["match_reasons"] = reasons[:3]
            scored.append(serialized)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify({
        "success": True,
        "query": query_text,
        "results": scored[:20]
    })


@meals_bp.get("")
def list_meals():
    """
    GET /api/meals

    Query parameters (all optional):
      q, restaurant_id, category_id, cuisine, meal_type, food_type,
      dietary_preference, spice_level, min_price, max_price,
      sort (name | price_asc | price_desc), page, page_size
    """
    args = request.args
    try:
        filters = {
            "q": parse_text(args.get("q"), "q"),
            "restaurant_id": parse_positive_int(
                args.get("restaurant_id"), "restaurant_id"
            ),
            "category_id": parse_positive_int(
                args.get("category_id"), "category_id"
            ),
            "min_price": parse_price(args.get("min_price"), "min_price"),
            "max_price": parse_price(args.get("max_price"), "max_price"),
        }
        for name in TEXT_FILTER_NAMES:
            filters[name] = parse_text(args.get(name), name)

        if (
            filters["min_price"] is not None
            and filters["max_price"] is not None
            and filters["min_price"] > filters["max_price"]
        ):
            raise QueryParamError(
                "min_price cannot be greater than max_price."
            )

        sort = (args.get("sort") or "name").strip()
        if sort not in meal_service.SORT_OPTIONS:
            raise QueryParamError(
                "sort must be one of: "
                + ", ".join(meal_service.SORT_OPTIONS) + "."
            )
        page, page_size = parse_pagination(args)
    except QueryParamError as error:
        return _bad_request(str(error))

    meals, pagination = meal_service.list_meals(
        filters, sort, page, page_size
    )
    return jsonify(
        {"success": True, "meals": meals, "pagination": pagination}
    )


@meals_bp.get("/filters")
def meal_filter_options():
    """Distinct values that can be used as filters (from the database)."""
    return jsonify(
        {"success": True, "filters": meal_service.get_filter_options()}
    )


@meals_bp.get("/<meal_id>")
def meal_detail(meal_id):
    try:
        parsed_id = parse_positive_int(meal_id, "meal id")
    except QueryParamError as error:
        return _bad_request(str(error))
    if parsed_id is None:
        return _bad_request("meal id must be a positive whole number.")

    meal = meal_service.get_meal(parsed_id)
    if meal is None:
        return jsonify({"success": False, "error": "Meal not found."}), 404
    return jsonify({"success": True, "meal": meal})


@categories_bp.get("")
def list_categories():
    """Active food categories."""
    return jsonify(
        {"success": True, "categories": meal_service.list_categories()}
    )
