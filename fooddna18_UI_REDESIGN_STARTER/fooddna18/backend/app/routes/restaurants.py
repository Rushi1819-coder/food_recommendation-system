from flask import Blueprint, jsonify, request

from ..services import restaurant_service
from ..utils.query_params import (
    QueryParamError,
    parse_pagination,
    parse_positive_int,
    parse_text,
)

restaurants_bp = Blueprint(
    "restaurants", __name__, url_prefix="/api/restaurants"
)


def _bad_request(message):
    return jsonify({"success": False, "error": message}), 400


@restaurants_bp.get("")
def list_restaurants():
    """GET /api/restaurants?q=&page=&page_size="""
    try:
        search = parse_text(request.args.get("q"), "q")
        page, page_size = parse_pagination(request.args)
    except QueryParamError as error:
        return _bad_request(str(error))

    restaurants, pagination = restaurant_service.list_restaurants(
        search, page, page_size
    )
    return jsonify(
        {"success": True, "restaurants": restaurants, "pagination": pagination}
    )


@restaurants_bp.get("/<restaurant_id>")
def restaurant_detail(restaurant_id):
    try:
        parsed_id = parse_positive_int(restaurant_id, "restaurant id")
    except QueryParamError as error:
        return _bad_request(str(error))
    if parsed_id is None:
        return _bad_request("restaurant id must be a positive whole number.")

    restaurant = restaurant_service.get_restaurant(parsed_id)
    if restaurant is None:
        return jsonify(
            {"success": False, "error": "Restaurant not found."}
        ), 404
    return jsonify({"success": True, "restaurant": restaurant})
