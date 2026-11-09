"""Food Memory API (Phase 5): events the browser can report itself."""

from flask import Blueprint, jsonify, request

from ..middleware.auth import csrf_protected, role_required
from ..services import food_memory_service, meal_service
from ..utils.query_params import QueryParamError, parse_positive_int

food_memory_bp = Blueprint(
    "food_memory", __name__, url_prefix="/api/food-memory"
)


def _fail(message, status):
    return jsonify({"success": False, "error": message}), status


@food_memory_bp.post("/meal-views")
@role_required("customer")
@csrf_protected
def record_meal_view(user):
    """
    POST /api/food-memory/meal-views   body: {"meal_id": 12}

    Records that the customer opened a meal's detail page. Only publicly
    visible meals are accepted, and repeat views within 30 minutes are not
    stored again.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("Request body must be a JSON object.", 400)

    raw = data.get("meal_id")
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        return _fail("meal_id must be a positive whole number.", 400)
    try:
        meal_id = parse_positive_int(str(raw), "meal_id")
    except QueryParamError as error:
        return _fail(str(error), 400)
    if meal_id is None:
        return _fail("meal_id must be a positive whole number.", 400)

    meal = meal_service.get_meal(meal_id)
    if meal is None:
        return _fail("Meal not found.", 404)

    row = food_memory_service.record_event(
        user.id,
        "meal_viewed",
        meal_id=meal_id,
        restaurant_id=meal["restaurant"]["id"],
    )
    return jsonify({"success": True, "recorded": row is not None})
