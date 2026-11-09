"""
Customer food preferences (Phase 5).

One row per user in `user_preferences` (the table has UNIQUE(user_id)).
Everything here takes the user id from the caller, which always passes the
authenticated user's id; nothing in this module reads a user id from request
data.

PUT semantics: the payload is the COMPLETE set of preferences. A field that
is missing, null or blank is stored as NULL ("no preference").
"""

import re
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import UserPreference
from ..utils.query_params import QueryParamError, parse_price

# (field name, human label, maximum length = the column size in models.py)
TEXT_FIELDS = (
    ("cuisine", "Cuisine", 80),
    ("meal_type", "Meal type", 50),
    ("taste", "Taste", 50),
    ("spice_level", "Spice level", 30),
    ("portion_size", "Portion size", 30),
    ("food_type", "Food type", 30),
    ("dietary_preference", "Dietary preference", 80),
)
PREFERENCE_FIELDS = tuple(name for name, _, _ in TEXT_FIELDS) + ("budget",)

# Letters, digits, space and a few punctuation marks used in food names
# ("Gluten-Free", "Non-Veg", "Rice & Curry", "High-Protein (low carb)").
_TEXT_PATTERN = re.compile(r"^[\w '&().,/+-]+$")


def _clean_text(value, label, max_length):
    """Return trimmed text, or None for blank. Raises ValueError (user-safe)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if value == "":
        return None
    if len(value) > max_length:
        raise ValueError(f"{label} must be at most {max_length} characters.")
    if not _TEXT_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} may contain only letters, numbers, spaces and "
            "the characters ' & ( ) . , / + -"
        )
    return value


def _clean_budget(value):
    """Budget = the most the customer wants to pay for ONE meal."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Budget must be a number.")
    try:
        amount = parse_price(str(value), "Budget")
    except QueryParamError as error:
        raise ValueError(str(error))
    if amount is None:
        return None
    if amount <= Decimal("0"):
        raise ValueError("Budget must be greater than 0.")
    return amount


def validate_preferences(data):
    """
    Validate a preferences payload.

    Returns (cleaned, errors). `cleaned` always has every field in
    PREFERENCE_FIELDS (None = no preference); `errors` maps field name to a
    message and is empty when the payload is valid. Unknown keys (for
    example a `user_id` sent by a browser) are ignored.
    """
    cleaned = {}
    errors = {}

    for name, label, max_length in TEXT_FIELDS:
        try:
            cleaned[name] = _clean_text(data.get(name), label, max_length)
        except ValueError as error:
            errors[name] = str(error)

    try:
        cleaned["budget"] = _clean_budget(data.get("budget"))
    except ValueError as error:
        errors["budget"] = str(error)

    return cleaned, errors


def get_preference_row(user_id):
    return UserPreference.query.filter_by(user_id=user_id).first()


def has_any_preference(values):
    """True if at least one preference field holds a value."""
    return any(values.get(name) is not None for name in PREFERENCE_FIELDS)


def serialize_preferences(row):
    """None when the customer has never saved preferences."""
    if row is None:
        return None
    data = {name: getattr(row, name) for name in PREFERENCE_FIELDS}
    if row.budget is not None:
        data["budget"] = str(Decimal(row.budget).quantize(Decimal("0.01")))
    data["updated_at"] = row.updated_at.isoformat() + "Z"
    return data


def save_preferences(user_id, cleaned):
    """
    Create or update the user's single preference row.

    Returns (row, created). Two simultaneous first saves hit the UNIQUE
    constraint on user_id; the loser rolls back and updates instead, so a
    second row is never created.
    """
    row = get_preference_row(user_id)
    created = row is None

    if created:
        row = UserPreference(user_id=user_id)
        db.session.add(row)

    for name in PREFERENCE_FIELDS:
        setattr(row, name, cleaned[name])

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        row = get_preference_row(user_id)
        if row is None:
            raise
        created = False
        for name in PREFERENCE_FIELDS:
            setattr(row, name, cleaned[name])
        db.session.commit()

    return row, created
