"""Public meal and category browsing (read-only)."""

from decimal import Decimal

from sqlalchemy import func, or_

from ..extensions import db
from ..models import FoodCategory, Meal, Restaurant
from ..utils.query_params import escape_like, pagination_block
from .restaurant_service import visible_meal_filters

SORT_OPTIONS = {
    "name": (Meal.name.asc(), Meal.id.asc()),
    "price_asc": (Meal.price.asc(), Meal.name.asc(), Meal.id.asc()),
    "price_desc": (Meal.price.desc(), Meal.name.asc(), Meal.id.asc()),
}

# Exact-match (case-insensitive under the utf8mb4_unicode_ci collation).
TEXT_FILTERS = {
    "cuisine": Meal.cuisine,
    "meal_type": Meal.meal_type,
    "food_type": Meal.food_type,
    "dietary_preference": Meal.dietary_preference,
    "spice_level": Meal.spice_level,
}


def _safe_image_url(url):
    """Only http(s) image links are returned; anything else becomes None."""
    if url and url.lower().startswith(("http://", "https://")):
        return url
    return None


def _money(value):
    return str(Decimal(value).quantize(Decimal("0.01")))


def serialize_meal(meal, restaurant, category, detail=False):
    restaurant_data = {"id": restaurant.id, "name": restaurant.name}
    if detail:
        restaurant_data["address"] = restaurant.address
    return {
        "id": meal.id,
        "name": meal.name,
        "description": meal.description,
        "price": _money(meal.price),
        "cuisine": meal.cuisine,
        "meal_type": meal.meal_type,
        "taste": meal.taste,
        "spice_level": meal.spice_level,
        "portion_size": meal.portion_size,
        "dietary_preference": meal.dietary_preference,
        "food_type": meal.food_type,
        "image_url": _safe_image_url(meal.image_url),
        "restaurant": restaurant_data,
        "category": {"id": category.id, "name": category.name},
    }


def _visible_meal_query(*entities):
    return (
        db.session.query(*entities)
        .select_from(Meal)
        .join(Restaurant, Restaurant.id == Meal.restaurant_id)
        .join(FoodCategory, FoodCategory.id == Meal.category_id)
        .filter(*visible_meal_filters())
    )


def list_meals(filters, sort, page, page_size):
    query = _visible_meal_query(Meal, Restaurant, FoodCategory)

    if filters.get("q"):
        pattern = f"%{escape_like(filters['q'])}%"
        query = query.filter(
            or_(
                Meal.name.like(pattern, escape="\\"),
                Meal.description.like(pattern, escape="\\"),
            )
        )
    if filters.get("restaurant_id"):
        query = query.filter(Meal.restaurant_id == filters["restaurant_id"])
    if filters.get("category_id"):
        query = query.filter(Meal.category_id == filters["category_id"])
    for name, column in TEXT_FILTERS.items():
        if filters.get(name):
            query = query.filter(column == filters[name])
    if filters.get("min_price") is not None:
        query = query.filter(Meal.price >= filters["min_price"])
    if filters.get("max_price") is not None:
        query = query.filter(Meal.price <= filters["max_price"])

    total = query.count()
    rows = (
        query.order_by(*SORT_OPTIONS[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return (
        [serialize_meal(m, r, c) for m, r, c in rows],
        pagination_block(page, page_size, total),
    )


def get_meal(meal_id):
    row = (
        _visible_meal_query(Meal, Restaurant, FoodCategory)
        .filter(Meal.id == meal_id)
        .first()
    )
    if row is None:
        return None
    return serialize_meal(*row, detail=True)


def visible_meal_rows():
    """
    Every publicly visible meal as (Meal, Restaurant, FoodCategory) rows.

    Phase 5 (recommendations) reuses the Phase 4 visibility rule through
    this function, so a meal that cannot be browsed can never be
    recommended. No pagination: the scorer ranks the whole visible
    catalogue.
    """
    return (
        _visible_meal_query(Meal, Restaurant, FoodCategory)
        .order_by(Meal.id.asc())
        .all()
    )


def list_categories():
    counts = (
        _visible_meal_query(
            Meal.category_id.label("cid"), func.count(Meal.id).label("n")
        )
        .group_by(Meal.category_id)
        .subquery()
    )
    rows = (
        db.session.query(FoodCategory, counts.c.n)
        .outerjoin(counts, counts.c.cid == FoodCategory.id)
        .filter(FoodCategory.is_active.is_(True))
        .order_by(FoodCategory.name.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "meal_count": int(n or 0),
        }
        for c, n in rows
    ]


def get_filter_options():
    """Distinct values among publicly visible meals, for filter dropdowns."""

    def distinct(column):
        rows = (
            _visible_meal_query(column)
            .filter(column.isnot(None), column != "")
            .distinct()
            .order_by(column.asc())
            .all()
        )
        return [r[0] for r in rows]

    low, high = _visible_meal_query(
        func.min(Meal.price), func.max(Meal.price)
    ).one()
    return {
        "cuisines": distinct(Meal.cuisine),
        "meal_types": distinct(Meal.meal_type),
        "food_types": distinct(Meal.food_type),
        "dietary_preferences": distinct(Meal.dietary_preference),
        "spice_levels": distinct(Meal.spice_level),
        # Added in Phase 5 (preference form dropdowns).
        "tastes": distinct(Meal.taste),
        "portion_sizes": distinct(Meal.portion_size),
        "price_range": {
            "min": _money(low) if low is not None else None,
            "max": _money(high) if high is not None else None,
        },
    }
