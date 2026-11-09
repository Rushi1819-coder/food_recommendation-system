"""Public restaurant browsing (read-only)."""

from sqlalchemy import func

from ..extensions import db
from ..models import FoodCategory, Meal, Restaurant
from ..utils.query_params import escape_like, pagination_block

# A restaurant is publicly visible only once the Super Admin has approved
# it. New applications are created as "pending" (see auth_service).
PUBLIC_RESTAURANT_STATUS = "approved"


def public_restaurant_filter():
    return Restaurant.status == PUBLIC_RESTAURANT_STATUS


def visible_meal_filters():
    """Conditions that make a meal publicly visible (shared with meals)."""
    return (
        Meal.is_available.is_(True),
        FoodCategory.is_active.is_(True),
        Restaurant.status == PUBLIC_RESTAURANT_STATUS,
    )


def _meal_count_subquery():
    return (
        db.session.query(
            Meal.restaurant_id.label("restaurant_id"),
            func.count(Meal.id).label("meal_count"),
        )
        .join(FoodCategory, FoodCategory.id == Meal.category_id)
        .filter(Meal.is_available.is_(True), FoodCategory.is_active.is_(True))
        .group_by(Meal.restaurant_id)
        .subquery()
    )


def serialize_restaurant(restaurant, meal_count, detail=False):
    data = {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "address": restaurant.address,
        "meal_count": int(meal_count or 0),
    }
    if detail:
        data["phone"] = restaurant.phone
    return data


def list_restaurants(search, page, page_size):
    counts = _meal_count_subquery()
    query = (
        db.session.query(Restaurant, counts.c.meal_count)
        .outerjoin(counts, counts.c.restaurant_id == Restaurant.id)
        .filter(public_restaurant_filter())
    )
    if search:
        query = query.filter(
            Restaurant.name.like(f"%{escape_like(search)}%", escape="\\")
        )

    total = query.count()
    rows = (
        query.order_by(Restaurant.name.asc(), Restaurant.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return (
        [serialize_restaurant(r, c) for r, c in rows],
        pagination_block(page, page_size, total),
    )


def get_restaurant(restaurant_id):
    counts = _meal_count_subquery()
    row = (
        db.session.query(Restaurant, counts.c.meal_count)
        .outerjoin(counts, counts.c.restaurant_id == Restaurant.id)
        .filter(Restaurant.id == restaurant_id, public_restaurant_filter())
        .first()
    )
    if row is None:
        return None
    return serialize_restaurant(row[0], row[1], detail=True)
