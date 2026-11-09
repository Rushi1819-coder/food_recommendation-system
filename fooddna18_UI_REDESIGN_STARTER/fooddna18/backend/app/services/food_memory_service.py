"""
Food Memory: a small log of what a customer did with meals (Phase 5).

This is the ONLY place that writes `food_memory` rows, so later modules
(cart, ordering) record their events through `record_event` instead of
duplicating the logic. To add an event: add one entry to EVENT_TYPES and
call `record_event(...)` from the new feature.

Only events the application can actually record today are registered.
Rows hold ids and a few small, server-built facts. They never hold
passwords, session data, e-mail addresses or free text typed by the user.
"""

from datetime import datetime, timedelta

from ..extensions import db
from ..models import FoodMemory

# event_type -> minutes during which an identical event (same user, same
# meal) is NOT stored again. This keeps page refreshes from flooding the
# table. 0 means "always store".
EVENT_TYPES = {
    "meal_viewed": 30,
    "recommendations_viewed": 5,
    "recommendation_selected": 0,
    # Phase 6: shopping cart and order placement events.
    "added_to_cart": 0,
    "order_placed": 0,
    # Phase 9/10 operational events.
    "order_status_changed": 0,
    "feedback_submitted": 0,
}

MAX_DATA_KEYS = 6
MAX_DATA_TEXT = 100


def _check_event_data(data):
    """event_data must be a small flat dict of simple values."""
    if data is None:
        return None
    if not isinstance(data, dict) or len(data) > MAX_DATA_KEYS:
        raise ValueError("event_data must be a small dictionary.")
    for key, value in data.items():
        if not isinstance(key, str) or len(key) > MAX_DATA_TEXT:
            raise ValueError("event_data keys must be short text.")
        if isinstance(value, str):
            if len(value) > MAX_DATA_TEXT:
                raise ValueError("event_data text values are too long.")
        elif value is not None and not isinstance(value, (bool, int, float)):
            raise ValueError("event_data values must be simple values.")
    return data


def record_event(
    user_id,
    event_type,
    meal_id=None,
    restaurant_id=None,
    data=None,
    commit=True,
    now=None,
):
    """
    Store one Food Memory event. Returns the new row, or None when an
    identical recent event made it a duplicate.

    Raises ValueError for an unknown event type or oversized event_data.
    With commit=False the caller owns the transaction.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown food memory event type: {event_type}")
    data = _check_event_data(data)
    now = now or datetime.utcnow()

    window = EVENT_TYPES[event_type]
    if window:
        query = FoodMemory.query.filter(
            FoodMemory.user_id == user_id,
            FoodMemory.event_type == event_type,
            FoodMemory.created_at >= now - timedelta(minutes=window),
        )
        # meal_id may be NULL (e.g. "recommendations_viewed"); compare the
        # same way for both cases.
        if meal_id is None:
            query = query.filter(FoodMemory.meal_id.is_(None))
        else:
            query = query.filter(FoodMemory.meal_id == meal_id)
        if query.first() is not None:
            return None

    row = FoodMemory(
        user_id=user_id,
        meal_id=meal_id,
        restaurant_id=restaurant_id,
        event_type=event_type,
        event_data=data,
    )
    db.session.add(row)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return row


def recent_events(user_id, limit=20):
    """The user's own most recent events (newest first)."""
    return (
        FoodMemory.query.filter_by(user_id=user_id)
        .order_by(FoodMemory.id.desc())
        .limit(limit)
        .all()
    )
