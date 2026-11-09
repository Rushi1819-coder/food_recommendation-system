"""Customer food preferences API (Phase 5).

The user is always the authenticated session user. A `user_id` in the
request is never read, so a customer can only ever see or change their own
preference row.
"""

from flask import Blueprint, jsonify, request

from ..middleware.auth import csrf_protected, role_required
from ..services import preference_service

preferences_bp = Blueprint(
    "preferences", __name__, url_prefix="/api/preferences"
)


def _fail(message, status, **extra):
    return jsonify({"success": False, "error": message, **extra}), status


@preferences_bp.get("")
@role_required("customer")
def get_preferences(user):
    """The customer's saved preferences (`preferences` is null if none)."""
    row = preference_service.get_preference_row(user.id)
    data = preference_service.serialize_preferences(row)
    return jsonify(
        {
            "success": True,
            "preferences": data,
            "has_preferences": bool(
                data and preference_service.has_any_preference(data)
            ),
        }
    )


@preferences_bp.put("")
@role_required("customer")
@csrf_protected
def save_preferences(user):
    """
    Create or replace the customer's preferences.

    The body is the complete set; a missing, null or blank field clears
    that preference. A body that is not a JSON object is rejected (never
    treated as "clear everything").
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("Request body must be a JSON object.", 400)

    cleaned, errors = preference_service.validate_preferences(data)
    if errors:
        return _fail(
            "Please correct the highlighted preferences.", 400, errors=errors
        )

    row, created = preference_service.save_preferences(user.id, cleaned)
    return (
        jsonify(
            {
                "success": True,
                "message": "Preferences saved.",
                "created": created,
                "preferences": preference_service.serialize_preferences(row),
            }
        ),
        201 if created else 200,
    )
