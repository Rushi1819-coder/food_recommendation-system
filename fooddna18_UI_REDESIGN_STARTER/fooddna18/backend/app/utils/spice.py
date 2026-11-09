"""
FoodDNA — Canonical spice-level definitions (fix for issue 1.5).

A single source of truth so that the recommender, meal form
validation, preference dropdowns and seed data all use identical
values.  Any part of the codebase that references spice levels
imports from here instead of using magic strings.

Canonical scale (ordered mild → hot):
    None / not specified
    Mild
    Medium
    Hot
    Very Hot

Aliases: historical / alternate spellings map to the canonical form.
Matching is always case-insensitive.
"""

# Ordered list: index position is used for adjacent-step partial credit.
SPICE_SCALE = [None, "Mild", "Medium", "Hot", "Very Hot"]

# Maps lower-cased alternate spellings → canonical form.
SPICE_ALIASES: dict[str, str] = {
    "none": None,
    "no spice": None,
    "not spicy": None,
    "mild": "Mild",
    "medium": "Medium",
    "med": "Medium",
    "hot": "Hot",
    "spicy": "Hot",
    "very hot": "Very Hot",
    "extra hot": "Very Hot",
    "extra-hot": "Very Hot",
    "veryhot": "Very Hot",
    "xhot": "Very Hot",
}

# Credit fraction for a one-step-away neighbour (e.g. Medium vs Hot).
NEIGHBOUR_CREDIT = 0.5


def normalize_spice(value: str | None) -> str | None:
    """
    Return the canonical spice-level string (or None) for any input.
    Accepts the canonical form, any alias, or None / blank.
    Raises ValueError for unrecognised non-blank strings.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Spice level must be a string, got {type(value).__name__}.")
    stripped = value.strip()
    if not stripped:
        return None
    key = stripped.casefold()
    # Direct alias lookup
    if key in SPICE_ALIASES:
        return SPICE_ALIASES[key]
    # Accept the canonical form regardless of case
    for canonical in SPICE_SCALE:
        if canonical and canonical.casefold() == key:
            return canonical
    raise ValueError(
        f"Unknown spice level: '{value}'. "
        f"Accepted values: {', '.join(s for s in SPICE_SCALE if s)}."
    )


def spice_score(pref: str | None, meal: str | None) -> float:
    """
    Return 1.0 (full match), NEIGHBOUR_CREDIT (one step away),
    or 0.0 (no match) for a preference / meal pair.
    Both arguments are normalized before comparison.
    """
    try:
        pref_norm = normalize_spice(pref)
        meal_norm = normalize_spice(meal)
    except ValueError:
        return 0.0

    if pref_norm is None or meal_norm is None:
        # No preference set — no penalty and no bonus.
        return 0.0

    if pref_norm == meal_norm:
        return 1.0

    pref_idx = SPICE_SCALE.index(pref_norm) if pref_norm in SPICE_SCALE else -1
    meal_idx = SPICE_SCALE.index(meal_norm) if meal_norm in SPICE_SCALE else -1

    if pref_idx >= 0 and meal_idx >= 0 and abs(pref_idx - meal_idx) == 1:
        return NEIGHBOUR_CREDIT

    return 0.0
