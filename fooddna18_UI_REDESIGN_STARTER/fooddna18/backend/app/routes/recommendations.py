"""Personalised recommendation API (Phase 5)."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..middleware.auth import csrf_protected, role_required
from ..services import (
    food_memory_service,
    meal_service,
    recommendation_service,
)
from ..utils.query_params import (
    QueryParamError,
    parse_pagination,
    parse_positive_int,
)

recommendations_bp = Blueprint(
    "recommendations", __name__, url_prefix="/api/recommendations"
)


def _fail(message, status):
    return jsonify({"success": False, "error": message}), status


def _parse_limit(raw):
    """`raw` is text, an int, or None. Returns a limit in 1..MAX_LIMIT."""
    if raw is None:
        return recommendation_service.DEFAULT_LIMIT
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        raise QueryParamError("limit must be a positive whole number.")
    value = parse_positive_int(str(raw), "limit")
    if value is None:
        return recommendation_service.DEFAULT_LIMIT
    if value > recommendation_service.MAX_LIMIT:
        raise QueryParamError(
            f"limit must be at most {recommendation_service.MAX_LIMIT}."
        )
    return value


def _optional_json_body():
    """{} for an empty body; QueryParamError if a body is not an object."""
    data = request.get_json(silent=True)
    if data is None:
        if request.get_data():
            raise QueryParamError("Request body must be a JSON object.")
        return {}
    if not isinstance(data, dict):
        raise QueryParamError("Request body must be a JSON object.")
    return data


@recommendations_bp.get("")
@role_required("customer")
def get_recommendations(user):
    """
    GET /api/recommendations?limit=10

    Computes recommendations from the customer's saved preferences. Read
    only: nothing is stored. Use POST to also record history.
    """
    try:
        limit = _parse_limit(request.args.get("limit"))
    except QueryParamError as error:
        return _fail(str(error), 400)

    result = recommendation_service.compute_recommendations(user.id, limit)
    return jsonify({"success": True, **result})


@recommendations_bp.post("")
@role_required("customer")
@csrf_protected
def generate_recommendations(user):
    """
    POST /api/recommendations   body (optional): {"limit": 10}

    Computes recommendations, stores them in the customer's recommendation
    history (a repeat of the same meal within an hour refreshes the old row
    instead of adding one) and records a Food Memory event.
    """
    try:
        body = _optional_json_body()
        limit = _parse_limit(body.get("limit"))
    except QueryParamError as error:
        return _fail(str(error), 400)

    result = recommendation_service.compute_recommendations(user.id, limit)
    history = recommendation_service.record_recommendations(
        user.id, result["recommendations"]
    )

    if result["recommendations"]:
        # Food Memory is best-effort: a failure here must not hide the
        # recommendations that were already saved.
        try:
            food_memory_service.record_event(
                user.id,
                "recommendations_viewed",
                data={"returned": len(result["recommendations"]),
                      "limit": limit},
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Food memory write failed")

    return jsonify({"success": True, "history": history, **result})


@recommendations_bp.get("/history")
@role_required("customer")
def recommendation_history(user):
    """The customer's own past recommendations, newest first."""
    try:
        page, page_size = parse_pagination(request.args)
    except QueryParamError as error:
        return _fail(str(error), 400)

    items, total = recommendation_service.list_history(
        user.id, page, page_size
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return jsonify(
        {
            "success": True,
            "history": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": pages,
            },
        }
    )


@recommendations_bp.post("/<meal_id>/select")
@role_required("customer")
@csrf_protected
def select_recommendation(user, meal_id):
    """
    Record that the customer opened a recommended meal. Only meals that
    were actually recommended to THIS customer, and are still visible,
    are accepted.
    """
    try:
        parsed = parse_positive_int(meal_id, "meal id")
    except QueryParamError as error:
        return _fail(str(error), 400)
    if parsed is None:
        return _fail("meal id must be a positive whole number.", 400)

    if not recommendation_service.was_recommended(user.id, parsed):
        return _fail("This meal was not recommended to you.", 404)

    meal = meal_service.get_meal(parsed)
    if meal is None:
        return _fail("Meal not found.", 404)

    row = food_memory_service.record_event(
        user.id,
        "recommendation_selected",
        meal_id=parsed,
        restaurant_id=meal["restaurant"]["id"],
    )
    return jsonify({"success": True, "recorded": row is not None})
