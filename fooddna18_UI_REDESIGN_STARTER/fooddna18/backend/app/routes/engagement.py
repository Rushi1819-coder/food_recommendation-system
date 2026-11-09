"""Phase 10: public offers, customer feedback and notification inbox."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.auth import csrf_protected, role_required
from ..models import Feedback, FoodMemory, Meal, Notification, Offer, Order, OrderItem, Restaurant, RestaurantAdmin
from ..services import food_memory_service

engagement_bp = Blueprint("engagement", __name__, url_prefix="/api")


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _my_restaurant(user):
    link = RestaurantAdmin.query.filter_by(user_id=user.id).first()
    return db.session.get(Restaurant, link.restaurant_id) if link and link.restaurant_id else None


def _offer_json(row):
    restaurant = db.session.get(Restaurant, row.restaurant_id)
    return {"id": row.id, "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant.name if restaurant else None,
        "title": row.title, "description": row.description,
        "discount_percent": str(row.discount_percent),
        "start_date": row.start_date.isoformat(), "end_date": row.end_date.isoformat(),
        "is_active": bool(row.is_active)}


@engagement_bp.get("/offers")
def public_offers():
    today = date.today()
    rows = (Offer.query.join(Restaurant, Restaurant.id == Offer.restaurant_id)
        .filter(Offer.is_active.is_(True), Offer.start_date <= today,
                Offer.end_date >= today, Restaurant.status == "approved")
        .order_by(Offer.end_date.asc()).limit(100).all())
    return jsonify({"success": True, "offers": [_offer_json(row) for row in rows]})


@engagement_bp.get("/restaurant-admin/offers")
@role_required("restaurant_admin")
def restaurant_offers(user):
    restaurant = _my_restaurant(user)
    if not restaurant: return _fail("No restaurant is linked to this account.", 403)
    rows = Offer.query.filter_by(restaurant_id=restaurant.id).order_by(Offer.created_at.desc()).all()
    return jsonify({"success": True, "offers": [_offer_json(row) for row in rows]})


@engagement_bp.post("/restaurant-admin/offers")
@role_required("restaurant_admin")
@csrf_protected
def create_offer(user):
    restaurant = _my_restaurant(user)
    if not restaurant or restaurant.status != "approved": return _fail("An approved linked restaurant is required.", 403)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    title, start_raw, end_raw = data.get("title"), data.get("start_date"), data.get("end_date")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 150:
        return _fail("title is required and must be 150 characters or fewer.")
    try:
        discount = Decimal(str(data.get("discount_percent")))
        start_date = date.fromisoformat(str(start_raw)); end_date = date.fromisoformat(str(end_raw))
        if not discount.is_finite() or discount <= 0 or discount > 100 or end_date < start_date:
            raise ValueError()
    except (ValueError, TypeError, InvalidOperation): return _fail("Provide discount_percent from 0 to 100 and valid ordered ISO dates.")
    row = Offer(restaurant_id=restaurant.id, title=title.strip(), description=str(data.get("description") or "")[:5000] or None,
                discount_percent=discount, start_date=start_date, end_date=end_date, is_active=bool(data.get("is_active", True)))
    db.session.add(row); db.session.commit()
    return jsonify({"success": True, "offer": _offer_json(row)}), 201


@engagement_bp.patch("/restaurant-admin/offers/<int:offer_id>")
@role_required("restaurant_admin")
@csrf_protected
def update_offer(user, offer_id):
    restaurant = _my_restaurant(user); row = db.session.get(Offer, offer_id)
    if not restaurant or not row or row.restaurant_id != restaurant.id: return _fail("Offer not found.", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip() or len(data["title"].strip()) > 150: return _fail("Invalid title.")
        row.title = data["title"].strip()
    if "description" in data: row.description = str(data["description"] or "")[:5000] or None
    if "discount_percent" in data:
        try:
            discount = Decimal(str(data["discount_percent"]))
            if not discount.is_finite() or discount <= 0 or discount > 100: raise ValueError()
            row.discount_percent = discount
        except (ValueError, TypeError, InvalidOperation): return _fail("discount_percent must be greater than 0 and at most 100.")
    for key in ("start_date", "end_date"):
        if key in data:
            try: setattr(row, key, date.fromisoformat(str(data[key])))
            except ValueError: return _fail(f"{key} must use YYYY-MM-DD.")
    if row.end_date < row.start_date: return _fail("end_date cannot be before start_date.")
    if "is_active" in data: row.is_active = bool(data["is_active"])
    db.session.commit(); return jsonify({"success": True, "offer": _offer_json(row)})


@engagement_bp.get("/feedback")
@role_required("customer")
def my_feedback(user):
    rows = Feedback.query.filter_by(customer_id=user.id).order_by(Feedback.created_at.desc()).limit(100).all()
    return jsonify({"success": True, "feedback": [{"id": f.id, "food_id": f.food_id,
        "restaurant_id": f.restaurant_id, "rating": f.rating, "comment": f.comment,
        "created_at": f.created_at.isoformat() if f.created_at else None} for f in rows]})


@engagement_bp.post("/feedback")
@role_required("customer")
@csrf_protected
def submit_feedback(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    try:
        order_id = int(data.get("order_id")); meal_id = int(data.get("meal_id")); rating = int(data.get("rating"))
    except (ValueError, TypeError): return _fail("order_id, meal_id and integer rating are required.")
    if min(order_id, meal_id) < 1 or rating < 1 or rating > 5: return _fail("IDs must be positive and rating must be from 1 to 5.")
    comment = data.get("comment", "")
    if comment is not None and not isinstance(comment, str): return _fail("comment must be text.")
    if comment and len(comment) > 2000: return _fail("comment must be 2000 characters or fewer.")
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order or order.order_status != "delivered": return _fail("Feedback is available only for your delivered orders.", 403)
    item = OrderItem.query.filter_by(order_id=order.id, meal_id=meal_id).first()
    if not item: return _fail("That meal is not part of this order.", 400)
    previous = Feedback.query.filter_by(customer_id=user.id, food_id=meal_id, restaurant_id=order.restaurant_id).first()
    if previous: return _fail("You have already submitted feedback for this meal.", 409)
    row = Feedback(customer_id=user.id, food_id=meal_id, restaurant_id=order.restaurant_id,
                   rating=rating, comment=(comment or "").strip() or None)
    db.session.add(row)
    food_memory_service.record_event(user.id, "feedback_submitted", meal_id=meal_id,
        restaurant_id=order.restaurant_id, data={"rating": rating, "order_id": order.id}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "message": "Thank you for your feedback.", "feedback_id": row.id}), 201


@engagement_bp.get("/notifications")
@role_required("customer", "restaurant_admin", "staff", "delivery_partner", "super_admin")
def list_notifications(user):
    try: page = max(1, min(100000, int(request.args.get("page", "1"))))
    except ValueError: return _fail("page must be a positive integer.")
    page_size = 20; q = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc())
    total = q.count(); rows = q.offset((page-1)*page_size).limit(page_size).all()
    return jsonify({"success": True, "notifications": [{"id": n.id, "title": n.title,
        "message": n.message, "type": n.notification_type, "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat() if n.created_at else None} for n in rows],
        "unread_count": Notification.query.filter_by(user_id=user.id, is_read=False).count(),
        "pagination": {"page": page, "page_size": page_size, "total": total}})


@engagement_bp.patch("/notifications/<int:notification_id>/read")
@role_required("customer", "restaurant_admin", "staff", "delivery_partner", "super_admin")
@csrf_protected
def mark_notification_read(user, notification_id):
    row = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not row: return _fail("Notification not found.", 404)
    row.is_read = True; db.session.commit()
    return jsonify({"success": True, "message": "Notification marked as read."})


@engagement_bp.post("/notifications/read-all")
@role_required("customer", "restaurant_admin", "staff", "delivery_partner", "super_admin")
@csrf_protected
def mark_all_notifications_read(user):
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True}, synchronize_session=False)
    db.session.commit(); return jsonify({"success": True, "message": "Notifications marked as read."})


@engagement_bp.get("/food-memory/timeline")
@role_required("customer")
def food_memory_timeline(user):
    rows = FoodMemory.query.filter_by(user_id=user.id).order_by(FoodMemory.created_at.desc()).limit(100).all()
    return jsonify({"success": True, "events": [{"id": r.id, "event_type": r.event_type,
        "meal_id": r.meal_id, "restaurant_id": r.restaurant_id,
        "event_data": r.event_data, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]})
