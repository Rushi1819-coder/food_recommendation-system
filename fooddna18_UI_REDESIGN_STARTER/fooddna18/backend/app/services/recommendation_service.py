"""
Personalised meal recommendations (Phase 5).

A transparent, rule-based scorer. There is no machine learning and no
external service: every score can be reproduced by hand from the customer's
saved preferences and the meal's database columns. The full method and its
limitations are documented in docs/RECOMMENDATIONS.md.

Pipeline (see `compute_recommendations`):
  1. read the customer's saved preferences
  2. read the meals that Phase 4 browsing shows publicly (available meal,
     active category, approved restaurant)
  3. drop meals that break a HARD rule (budget, veg/vegan food type,
     dietary preference)
  4. score the remaining meals against the SOFT preferences
  5. rank, keep the top `limit`, and explain each match

The scoring functions only read attributes from the objects they are given,
so they can be unit-tested without a database.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from ..extensions import db
from ..models import FoodCategory, Meal, Recommendation, Restaurant
from . import meal_service
from .preference_service import PREFERENCE_FIELDS, get_preference_row
from .restaurant_service import PUBLIC_RESTAURANT_STATUS

DEFAULT_LIMIT = 10
MAX_LIMIT = 30

# An identical (user, meal) recommendation generated within this many
# minutes is updated instead of stored again.
RECOMMENDATION_DEDUPE_MINUTES = 60

# Points per preference. A customer's score is
#   100 * (points earned) / (points available for the preferences they set)
# so a customer who sets only two preferences can still reach 100.
WEIGHTS = {
    "cuisine": Decimal("20"),
    "meal_type": Decimal("15"),
    "taste": Decimal("15"),
    "spice_level": Decimal("15"),
    "portion_size": Decimal("10"),
    "food_type": Decimal("10"),
    "dietary_preference": Decimal("10"),
    "budget": Decimal("5"),
}

SPICE_ORDER = ["none", "mild", "medium", "hot", "extra hot"]
SPICE_NEIGHBOUR_CREDIT = Decimal("0.5")  # one step away earns half the points

# Veg and Vegan are restrictions, so they are hard filters. "Non-Veg" is
# only a taste: people who eat meat also eat vegetarian food, so a Non-Veg
# preference just earns points and never removes vegetarian dishes.
STRICT_FOOD_TYPES = {
    "veg": {"veg", "vegan"},
    "vegan": {"vegan"},
}

# Dietary preference is a hard filter. A meal with no dietary label cannot
# be shown to be suitable, so it is excluded when a dietary preference is
# set. "Vegetarian" also accepts vegan dishes, "Eggetarian" also accepts
# vegetarian and vegan ones; any other label must match exactly.
DIETARY_COMPATIBLE = {
    "vegetarian": {"vegetarian", "vegan"},
    "eggetarian": {"eggetarian", "vegetarian", "vegan"},
}

EXCLUSION_ORDER = ("budget", "food_type", "dietary_preference")

MONEY = Decimal("0.01")


def _norm(value):
    """Case-insensitive comparison key; None for blank."""
    if isinstance(value, str) and value.strip():
        return value.strip().casefold()
    return None


def _money(value):
    return str(Decimal(value).quantize(MONEY))


class PreferenceProfile:
    """The customer's preferences, ready for scoring."""

    def __init__(self, values):
        self.values = {name: values.get(name) for name in PREFERENCE_FIELDS}
        budget = self.values.get("budget")
        self.budget = Decimal(str(budget)) if budget is not None else None
        # Only preferences the customer actually set take part.
        self.active = [
            name for name in PREFERENCE_FIELDS
            if self.values.get(name) not in (None, "")
        ]

    @classmethod
    def from_row(cls, row):
        if row is None:
            return cls({})
        return cls({name: getattr(row, name) for name in PREFERENCE_FIELDS})

    @property
    def is_empty(self):
        return not self.active

    def text(self, name):
        return self.values.get(name)

    def key(self, name):
        return _norm(self.values.get(name))

    def describe(self):
        """Preferences in use, JSON-ready (budget as a string)."""
        out = {}
        for name in self.active:
            value = self.values[name]
            out[name] = _money(value) if name == "budget" else value
        return out


# ---------------------------------------------------------------------------
# Hard rules
# ---------------------------------------------------------------------------

def failed_hard_rule(profile, meal):
    """Name of the first hard rule the meal breaks, or None if eligible."""
    if profile.budget is not None and Decimal(meal.price) > profile.budget:
        return "budget"

    wanted_type = profile.key("food_type")
    if wanted_type in STRICT_FOOD_TYPES:
        if _norm(meal.food_type) not in STRICT_FOOD_TYPES[wanted_type]:
            return "food_type"

    wanted_diet = profile.key("dietary_preference")
    if wanted_diet is not None:
        allowed = DIETARY_COMPATIBLE.get(wanted_diet, {wanted_diet})
        if _norm(meal.dietary_preference) not in allowed:
            return "dietary_preference"

    return None


# ---------------------------------------------------------------------------
# Scoring (call only for meals that passed the hard rules)
# ---------------------------------------------------------------------------

def _spice_distance(wanted, actual):
    """Steps between two spice levels, or None if either is unknown."""
    if wanted in SPICE_ORDER and actual in SPICE_ORDER:
        return abs(SPICE_ORDER.index(wanted) - SPICE_ORDER.index(actual))
    return None


def score_meal(profile, meal):
    """
    Score one eligible meal.

    Returns None when the customer set no preferences, or when the meal
    earned no points at all. Otherwise a dict:
      score    Decimal 0.00-100.00
      matched  preference names matched fully
      partial  preference names matched partly (spice level, one step away)
      reasons  human-readable sentences
    """
    if profile.is_empty:
        return None

    available = sum(WEIGHTS[name] for name in profile.active)
    earned = Decimal("0")
    matched, partial, reasons = [], [], []

    def full(name, text):
        nonlocal earned
        earned += WEIGHTS[name]
        matched.append(name)
        reasons.append(text)

    # Text attributes that must be equal.
    for name, label in (
        ("cuisine", "Cuisine"),
        ("meal_type", "Meal type"),
        ("taste", "Taste"),
        ("portion_size", "Portion size"),
    ):
        if name in profile.active and profile.key(name) == _norm(
            getattr(meal, name)
        ):
            full(name, f"{label} matches your preference: {getattr(meal, name)}")

    # Spice level: exact match, or half credit one step away.
    if "spice_level" in profile.active:
        wanted, actual = profile.key("spice_level"), _norm(meal.spice_level)
        if wanted == actual:
            full("spice_level", f"Spice level matches: {meal.spice_level}")
        else:
            distance = _spice_distance(wanted, actual)
            if distance == 1:
                earned += WEIGHTS["spice_level"] * SPICE_NEIGHBOUR_CREDIT
                partial.append("spice_level")
                reasons.append(
                    f"Spice level is close to your choice "
                    f"({meal.spice_level} instead of "
                    f"{profile.text('spice_level')})"
                )

    # Food type: exact match, or (for Veg/Vegan) any compatible type.
    if "food_type" in profile.active:
        wanted = profile.key("food_type")
        actual = _norm(meal.food_type)
        if wanted == actual:
            full("food_type", f"Food type matches: {meal.food_type}")
        elif wanted in STRICT_FOOD_TYPES and actual in STRICT_FOOD_TYPES[wanted]:
            full(
                "food_type",
                f"Suitable for your {profile.text('food_type')} "
                f"preference ({meal.food_type})",
            )

    # Dietary preference: a hard rule, so an eligible meal always satisfies it.
    if "dietary_preference" in profile.active:
        full(
            "dietary_preference",
            f"Meets your dietary preference: {profile.text('dietary_preference')}",
        )

    # Budget: also a hard rule.
    if "budget" in profile.active:
        full(
            "budget",
            f"Price {_money(meal.price)} is within your budget of "
            f"{_money(profile.budget)}",
        )

    if earned <= 0:
        return None

    score = (earned * 100 / available).quantize(MONEY)
    return {
        "score": score,
        "matched": matched,
        "partial": partial,
        "reasons": reasons,
    }


def rank_meals(profile, rows, limit):
    """
    Filter, score and rank (Meal, Restaurant, FoodCategory) rows.

    Returns (ranked, stats). `ranked` is the top `limit` entries sorted by
    score (highest first), then price (lowest first), then name, then id,
    so the order is always the same for the same data. `stats` counts what
    happened to every visible meal.
    """
    excluded = {rule: 0 for rule in EXCLUSION_ORDER}
    scored = []
    no_match = 0

    for meal, restaurant, category in rows:
        rule = failed_hard_rule(profile, meal)
        if rule is not None:
            excluded[rule] += 1
            continue
        result = score_meal(profile, meal)
        if result is None:
            no_match += 1
            continue
        scored.append((meal, restaurant, category, result))

    scored.sort(
        key=lambda item: (
            -item[3]["score"],
            Decimal(item[0].price),
            (item[0].name or "").casefold(),
            item[0].id,
        )
    )
    stats = {
        "visible_meals": len(rows),
        "excluded": excluded,
        "no_match": no_match,
        "eligible_and_scored": len(scored),
    }
    return scored[:limit], stats


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _message(profile, stats):
    if profile.is_empty:
        return (
            "You have not saved any food preferences yet. "
            "Set your preferences to get personalised recommendations."
        )
    if stats["visible_meals"] == 0:
        return "No meals are available right now. Please check back soon."
    if stats["eligible_and_scored"] == 0:
        if sum(stats["excluded"].values()) > 0 and stats["no_match"] == 0:
            return (
                "No available meals fit your budget, food type or dietary "
                "preference. Try raising your budget or relaxing a "
                "restriction."
            )
        return (
            "No available meals matched your preferences. "
            "Try choosing fewer or different preferences."
        )
    return None


def compute_recommendations(user_id, limit=DEFAULT_LIMIT):
    """
    Build recommendations for `user_id` (read-only; writes nothing).

    Returns a JSON-ready dict. A customer with no preferences, or with no
    matching meals, still gets a normal result with an empty list and a
    message; that is not an error.
    """
    profile = PreferenceProfile.from_row(get_preference_row(user_id))

    if profile.is_empty:
        stats = {
            "visible_meals": 0, "excluded": {r: 0 for r in EXCLUSION_ORDER},
            "no_match": 0, "eligible_and_scored": 0,
        }
        ranked = []
    else:
        rows = meal_service.visible_meal_rows()
        ranked, stats = rank_meals(profile, rows, limit)

    items = []
    for rank, (meal, restaurant, category, result) in enumerate(ranked, 1):
        items.append({
            "rank": rank,
            "score": str(result["score"]),
            "matched": result["matched"],
            "partial": result["partial"],
            "reasons": result["reasons"],
            "meal": meal_service.serialize_meal(meal, restaurant, category),
        })

    return {
        "has_preferences": not profile.is_empty,
        "preferences": profile.describe(),
        "recommendations": items,
        "summary": {
            "limit": limit,
            "returned": len(items),
            "visible_meals": stats["visible_meals"],
            "excluded": stats["excluded"],
            "no_match": stats["no_match"],
        },
        "message": _message(profile, stats),
    }


def record_recommendations(user_id, items, now=None):
    """
    Save the given recommendation items to the `recommendations` table.

    If the same meal was already recommended to this user within
    RECOMMENDATION_DEDUPE_MINUTES, that row is refreshed (score, reason,
    generated_at) instead of adding another one. Returns
    {"created": n, "updated": n}. Stores only ids, a score and the
    explanation text; nothing sensitive.
    """
    now = now or datetime.utcnow()
    if not items:
        return {"created": 0, "updated": 0}

    meal_ids = [item["meal"]["id"] for item in items]
    cutoff = now - timedelta(minutes=RECOMMENDATION_DEDUPE_MINUTES)
    existing = {}
    for row in (
        Recommendation.query.filter(
            Recommendation.user_id == user_id,
            Recommendation.meal_id.in_(meal_ids),
            Recommendation.generated_at >= cutoff,
        )
        .order_by(Recommendation.id.asc())
        .all()
    ):
        existing[row.meal_id] = row  # the newest row wins

    created = updated = 0
    for item in items:
        meal_id = item["meal"]["id"]
        score = Decimal(item["score"])
        reason = "; ".join(item["reasons"])
        row = existing.get(meal_id)
        if row is not None:
            row.score = score
            row.reason = reason
            row.generated_at = now
            updated += 1
        else:
            db.session.add(Recommendation(
                user_id=user_id, meal_id=meal_id, score=score,
                reason=reason, generated_at=now,
            ))
            created += 1

    db.session.commit()
    return {"created": created, "updated": updated}


def was_recommended(user_id, meal_id):
    """True if this meal appears in the user's own recommendation history."""
    return (
        db.session.query(Recommendation.id)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.meal_id == meal_id,
        )
        .first()
        is not None
    )


def list_history(user_id, page, page_size):
    """The user's own recommendation history, newest first."""
    query = (
        db.session.query(Recommendation, Meal, Restaurant, FoodCategory)
        .join(Meal, Meal.id == Recommendation.meal_id)
        .join(Restaurant, Restaurant.id == Meal.restaurant_id)
        .join(FoodCategory, FoodCategory.id == Meal.category_id)
        .filter(Recommendation.user_id == user_id)
    )
    total = query.count()
    rows = (
        query.order_by(
            Recommendation.generated_at.desc(), Recommendation.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for rec, meal, restaurant, category in rows:
        visible = (
            bool(meal.is_available)
            and bool(category.is_active)
            and restaurant.status == PUBLIC_RESTAURANT_STATUS
        )
        items.append({
            "id": rec.id,
            "score": _money(rec.score),
            "reason": rec.reason,
            "generated_at": rec.generated_at.isoformat() + "Z",
            "meal": {
                "id": meal.id,
                "name": meal.name,
                "price": _money(meal.price),
                "restaurant_name": restaurant.name,
            },
            "currently_available": visible,
        })
    return items, total
