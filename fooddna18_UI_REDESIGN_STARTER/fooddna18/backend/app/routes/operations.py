"""Operational workflows for Phases 7-9: dashboards, approvals, restaurant, staff and delivery."""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..middleware.auth import csrf_protected, role_required
from ..services import food_memory_service
from ..utils.validation import validate_email, validate_full_name, validate_password
from ..models import (AdminApproval, Cart, CartItem, DeliveryPartner, FoodCategory,
                      Meal, Notification, Order, OrderItem, OrderStatusHistory,
                      Payment, Restaurant, RestaurantAdmin, Staff, SystemActivity,
                      User, Role, Recommendation)

operations_bp = Blueprint("operations", __name__, url_prefix="/api")


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _notify(user_id, title, message, kind="general"):
    if user_id:
        db.session.add(Notification(user_id=user_id, title=title, message=message,
                                    notification_type=kind, is_read=False))


def _activity(user_id, action, description=""):
    db.session.add(SystemActivity(user_id=user_id, action=action,
                                  description=description[:2000] if description else None,
                                  ip_address=(request.remote_addr or "")[:45] or None))


def _admin_restaurant(user):
    link = RestaurantAdmin.query.filter_by(user_id=user.id).first()
    return db.session.get(Restaurant, link.restaurant_id) if link and link.restaurant_id else None


def _staff_restaurant(user):
    link = Staff.query.filter_by(user_id=user.id).first()
    return db.session.get(Restaurant, link.restaurant_id) if link else None


def _order_json(order):
    return {
        "id": order.id, "restaurant_id": order.restaurant_id,
        "restaurant_name": order.restaurant.name if order.restaurant else None,
        "user_id": order.user_id, "status": order.order_status,
        "subtotal": str(order.subtotal), "discount_amount": str(getattr(order, "discount_amount", 0) or 0),
        "offer_id": getattr(order, "offer_id", None), "delivery_fee": str(order.delivery_fee),
        "total_amount": str(order.total_amount), "delivery_address": order.delivery_address,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "item_count": sum(item.quantity for item in order.items),
        "delivery_partner_id": getattr(order, "delivery_partner_id", None),
    }


def _record_status(order, user, new_status, note=None):
    old = order.order_status
    order.order_status = new_status
    note_text = note.strip() if isinstance(note, str) else ""
    if not note_text:
        note_text = f"Status changed from {old} to {new_status}."
    db.session.add(OrderStatusHistory(order_id=order.id, status=new_status,
        changed_by=user.id, note=note_text[:255]))
    food_memory_service.record_event(order.user_id, "order_status_changed",
        restaurant_id=order.restaurant_id, data={"order_id": int(order.id), "status": new_status}, commit=False)
    _notify(order.user_id, f"Order #{order.id} update", f"Your order status is now {new_status.replace('_', ' ')}.", "order_status")
    _activity(user.id, "order_status_changed", f"Order {order.id}: {old} -> {new_status}")


# Phase 7: customer dashboard -------------------------------------------------
@operations_bp.get("/dashboard/customer")
@role_required("customer")
def customer_dashboard(user):
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.placed_at.desc()).limit(5).all()
    cart = Cart.query.filter_by(user_id=user.id).first()
    cart_count = sum(x.quantity for x in cart.items) if cart else 0
    recommendations_count = Recommendation.query.filter_by(user_id=user.id).count()
    return jsonify({"success": True, "summary": {
        "orders_total": Order.query.filter_by(user_id=user.id).count(),
        "orders_active": Order.query.filter(Order.user_id == user.id,
            Order.order_status.notin_(["delivered", "cancelled"])).count(),
        "cart_item_count": cart_count,
        "recommendations_count": recommendations_count,
        "recent_orders": [_order_json(o) for o in orders],
    }})


# Phase 8: Super Admin approvals and account management -----------------------
@operations_bp.get("/admin/approvals")
@role_required("super_admin")
def admin_list_approvals(user):
    status = (request.args.get("status") or "pending").strip().lower()
    if status not in {"pending", "approved", "rejected", "all"}:
        return _fail("status must be pending, approved, rejected or all.")
    q = AdminApproval.query.order_by(AdminApproval.created_at.desc())
    if status != "all": q = q.filter_by(status=status)
    rows = []
    for item in q.limit(200).all():
        applicant = db.session.get(User, item.user_id)
        restaurant = db.session.get(Restaurant, item.restaurant_id) if item.restaurant_id else None
        rows.append({"id": item.id, "user_id": item.user_id,
            "full_name": applicant.full_name if applicant else None,
            "email": applicant.email if applicant else None,
            "restaurant_id": item.restaurant_id,
            "restaurant_name": restaurant.name if restaurant else None,
            "approval_type": item.approval_type, "status": item.status,
            "remarks": item.remarks,
            "created_at": item.created_at.isoformat() if item.created_at else None})
    return jsonify({"success": True, "approvals": rows})


@operations_bp.patch("/admin/approvals/<int:approval_id>")
@role_required("super_admin")
@csrf_protected
def admin_review_approval(user, approval_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("status") not in {"approved", "rejected"}:
        return _fail("status must be approved or rejected.")
    approval = db.session.get(AdminApproval, approval_id)
    if not approval: return _fail("Approval not found.", 404)
    if approval.approval_type != "restaurant_admin":
        return _fail("This approval type is not supported by this screen.", 400)
    applicant = db.session.get(User, approval.user_id)
    restaurant = db.session.get(Restaurant, approval.restaurant_id) if approval.restaurant_id else None
    status = data["status"]
    approval.status = status
    approval.reviewed_by = user.id
    approval.reviewed_at = datetime.utcnow()
    approval.remarks = str(data.get("remarks") or "").strip()[:4000] or None
    if applicant:
        applicant.approval_status = status
        applicant.account_status = "active" if status == "approved" else "rejected"
    if restaurant:
        restaurant.status = status
    _notify(approval.user_id, "Restaurant application reviewed",
            f"Your restaurant administrator application was {status}.", "approval")
    _activity(user.id, "approval_reviewed", f"Approval {approval.id}: {status}")
    db.session.commit()
    return jsonify({"success": True, "message": f"Application {status}.", "approval_id": approval.id})


@operations_bp.get("/admin/users")
@role_required("super_admin")
def admin_list_users(user):
    role = (request.args.get("role") or "").strip()
    q = User.query.order_by(User.id.desc())
    if role:
        role_row = Role.query.filter_by(name=role).first()
        if not role_row: return _fail("Unknown role.")
        q = q.filter_by(role_id=role_row.id)
    result = []
    for row in q.limit(200).all():
        result.append({"id": row.id, "full_name": row.full_name, "email": row.email,
            "role": row.role.name if row.role else None, "account_status": row.account_status,
            "approval_status": row.approval_status, "is_active": bool(row.is_active)})
    return jsonify({"success": True, "users": result})


@operations_bp.post("/admin/users")
@role_required("super_admin")
@csrf_protected
def admin_create_operator(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    name, email, password, role_name = (data.get(k) for k in ("full_name", "email", "password", "role"))
    if not all(isinstance(v, str) and v.strip() for v in (name, email, password, role_name)):
        return _fail("full_name, email, password and role are required.")
    email = email.strip().lower(); role_name = role_name.strip()
    name_valid, name_error = validate_full_name(name)
    if not name_valid:
        return _fail(name_error)
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return _fail(email_error)
    password_valid, password_error = validate_password(password)
    if not password_valid:
        return _fail(password_error)
    if len(name.strip()) > 120 or len(email) > 254 or len(password) < 10 or len(password) > 200:
        return _fail("Name/email is too long, or password must be at least 10 characters.")
    if role_name not in {"staff", "delivery_partner"}:
        return _fail("Only staff and delivery_partner accounts can be created here.")
    if User.query.filter_by(email=email).first(): return _fail("An account with this email already exists.", 409)
    role_row = Role.query.filter_by(name=role_name).first()
    if not role_row: return _fail("Required role is not configured.", 500)
    restaurant_id = data.get("restaurant_id")
    restaurant = None
    if role_name == "staff":
        try: restaurant = db.session.get(Restaurant, int(restaurant_id))
        except (TypeError, ValueError): restaurant = None
        if not restaurant or restaurant.status != "approved": return _fail("staff requires an approved restaurant_id.")
    person = User(full_name=name.strip(), email=email, password_hash=generate_password_hash(password),
                  role_id=role_row.id, account_status="active", approval_status="not_required", is_active=True)
    db.session.add(person); db.session.flush()
    if role_name == "staff":
        db.session.add(Staff(user_id=person.id, restaurant_id=restaurant.id,
                             designation=(str(data.get("designation") or "Restaurant Staff")[:80])))
    else:
        db.session.add(DeliveryPartner(user_id=person.id, phone=str(data.get("phone") or "")[:20] or None,
                                       availability_status="available"))
    _activity(user.id, "operator_created", f"Created {role_name} account {person.id}")
    db.session.commit()
    return jsonify({"success": True, "user": {"id": person.id, "email": person.email, "role": role_name}}), 201


@operations_bp.get("/admin/restaurants")
@role_required("super_admin")
def admin_list_restaurants(user):
    status = (request.args.get("status") or "all").strip().lower()
    q = Restaurant.query.order_by(Restaurant.created_at.desc())
    if status != "all": q = q.filter_by(status=status)
    rows = q.limit(300).all()
    return jsonify({"success": True, "restaurants": [{"id": r.id, "name": r.name, "status": r.status,
        "address": r.address, "email": r.email} for r in rows]})


@operations_bp.patch("/admin/users/<int:user_id>/status")
@role_required("super_admin")
@csrf_protected
def admin_update_user_status(user, user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("account_status") not in {"active", "suspended"}:
        return _fail("account_status must be active or suspended.")
    target = db.session.get(User, user_id)
    if not target: return _fail("User not found.", 404)
    if target.id == user.id: return _fail("You cannot suspend your own account.", 400)
    target.account_status = data["account_status"]
    target.is_active = data["account_status"] == "active"
    _activity(user.id, "user_status_changed", f"User {target.id} status -> {target.account_status}")
    _notify(target.id, "Account status updated", f"Your account status is now {target.account_status}.", "account")
    db.session.commit()
    return jsonify({"success": True, "user_id": target.id, "account_status": target.account_status})


# Restaurant Admin -----------------------------------------------------------
@operations_bp.get("/restaurant-admin/dashboard")
@role_required("restaurant_admin")
def restaurant_admin_dashboard(user):
    restaurant = _admin_restaurant(user)
    if not restaurant: return _fail("No restaurant is linked to this account.", 403)
    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.placed_at.desc()).limit(10).all()
    return jsonify({"success": True, "restaurant": {"id": restaurant.id, "name": restaurant.name, "status": restaurant.status},
        "summary": {"orders_total": Order.query.filter_by(restaurant_id=restaurant.id).count(),
            "orders_active": Order.query.filter(Order.restaurant_id == restaurant.id, Order.order_status.notin_(["delivered", "cancelled"])).count(),
            "meals_total": Meal.query.filter_by(restaurant_id=restaurant.id).count(),
            "recent_orders": [_order_json(o) for o in orders]}})


@operations_bp.get("/restaurant-admin/orders")
@role_required("restaurant_admin")
def restaurant_admin_orders(user):
    restaurant = _admin_restaurant(user)
    if not restaurant: return _fail("No restaurant is linked to this account.", 403)
    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.placed_at.desc()).limit(100).all()
    return jsonify({"success": True, "orders": [_order_json(o) for o in orders]})


@operations_bp.patch("/restaurant-admin/orders/<int:order_id>/status")
@role_required("restaurant_admin")
@csrf_protected
def restaurant_admin_update_order(user, order_id):
    restaurant = _admin_restaurant(user)
    order = db.session.get(Order, order_id)
    if not restaurant or not order or order.restaurant_id != restaurant.id: return _fail("Order not found.", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    target = data.get("status")
    allowed = {"confirmed", "preparing", "ready_for_pickup", "cancelled"}
    if target not in allowed: return _fail("status must be confirmed, preparing, ready_for_pickup or cancelled.")
    transitions = {"pending": {"confirmed", "cancelled"}, "confirmed": {"preparing", "cancelled"},
                   "preparing": {"ready_for_pickup", "cancelled"}}
    if target not in transitions.get(order.order_status, set()): return _fail("Invalid order status transition.", 409)
    _record_status(order, user, target, data.get("note")); db.session.commit()
    return jsonify({"success": True, "order": _order_json(order)})


@operations_bp.get("/restaurant-admin/meals")
@role_required("restaurant_admin")
def restaurant_admin_meals(user):
    restaurant = _admin_restaurant(user)
    if not restaurant: return _fail("No restaurant is linked to this account.", 403)
    rows = Meal.query.filter_by(restaurant_id=restaurant.id).order_by(Meal.name.asc()).all()
    return jsonify({"success": True, "meals": [{"id": m.id, "name": m.name, "description": m.description,
        "price": str(m.price), "category_id": m.category_id, "is_available": bool(m.is_available),
        "cuisine": m.cuisine, "meal_type": m.meal_type, "taste": m.taste, "spice_level": m.spice_level,
        "portion_size": m.portion_size, "food_type": m.food_type, "dietary_preference": m.dietary_preference,
        "image_url": m.image_url} for m in rows]})


@operations_bp.post("/restaurant-admin/meals")
@role_required("restaurant_admin")
@csrf_protected
def restaurant_admin_create_meal(user):
    restaurant = _admin_restaurant(user)
    if not restaurant or restaurant.status != "approved": return _fail("An approved linked restaurant is required.", 403)
    data = request.get_json(silent=True)
    required = ("category_id", "name", "price", "cuisine", "meal_type", "taste", "spice_level", "portion_size", "food_type")
    if not isinstance(data, dict) or any(data.get(k) in (None, "") for k in required): return _fail("Missing required meal fields.")
    try:
        category = db.session.get(FoodCategory, int(data["category_id"]))
        price = Decimal(str(data["price"]))
        if not price.is_finite() or price < 0 or price > Decimal("99999999.99"): raise InvalidOperation()
    except (ValueError, TypeError, InvalidOperation): return _fail("category_id or price is invalid.")
    if not category or not category.is_active: return _fail("Choose an active category.")
    limits = {"name":150, "cuisine":80,"meal_type":50,"taste":50,"spice_level":30,"portion_size":30,"food_type":30,"dietary_preference":80,"image_url":500}
    if any(not isinstance(data.get(k), str) or len(data[k]) > limit for k,limit in limits.items() if data.get(k) is not None): return _fail("One or more meal fields have invalid text/length.")
    meal = Meal(restaurant_id=restaurant.id, category_id=category.id, name=data["name"].strip(), description=data.get("description"),
        price=price, cuisine=data["cuisine"].strip(), meal_type=data["meal_type"].strip(), taste=data["taste"].strip(),
        spice_level=data["spice_level"].strip(), portion_size=data["portion_size"].strip(), food_type=data["food_type"].strip(),
        dietary_preference=data.get("dietary_preference"), image_url=data.get("image_url"), is_available=bool(data.get("is_available", True)))
    db.session.add(meal); db.session.commit()
    return jsonify({"success": True, "meal": {"id": meal.id, "name": meal.name}}), 201


@operations_bp.patch("/restaurant-admin/meals/<int:meal_id>")
@role_required("restaurant_admin")
@csrf_protected
def restaurant_admin_update_meal(user, meal_id):
    restaurant = _admin_restaurant(user); meal = db.session.get(Meal, meal_id)
    if not restaurant or not meal or meal.restaurant_id != restaurant.id: return _fail("Meal not found.", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    allowed = {"name", "description", "price", "cuisine", "meal_type", "taste", "spice_level", "portion_size", "food_type", "dietary_preference", "image_url", "is_available", "category_id"}
    if set(data) - allowed: return _fail("Unsupported fields: " + ", ".join(sorted(set(data)-allowed)))
    for key, value in data.items():
        if key == "price":
            try:
                price = Decimal(str(value))
                if not price.is_finite() or price < 0: raise InvalidOperation()
                meal.price = price
            except (TypeError, ValueError, InvalidOperation): return _fail("price must be a non-negative decimal.")
        elif key == "category_id":
            try: category = db.session.get(FoodCategory, int(value))
            except (TypeError, ValueError): category = None
            if not category or not category.is_active: return _fail("Choose an active category.")
            meal.category_id = category.id
        elif key == "is_available": meal.is_available = bool(value)
        elif isinstance(value, str) or value is None: setattr(meal, key, value.strip() if isinstance(value,str) else None)
        else: return _fail(f"{key} has an invalid value.")
    db.session.commit(); return jsonify({"success": True, "message": "Meal updated."})


# Phase 9: restaurant staff and delivery partner ------------------------------
@operations_bp.get("/staff/dashboard")
@role_required("staff")
def staff_dashboard(user):
    restaurant = _staff_restaurant(user)
    if not restaurant: return _fail("No restaurant is linked to this staff account.", 403)
    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.placed_at.desc()).limit(50).all()
    return jsonify({"success": True, "restaurant": restaurant.name, "orders": [_order_json(o) for o in orders]})


@operations_bp.patch("/staff/orders/<int:order_id>/status")
@role_required("staff")
@csrf_protected
def staff_update_order(user, order_id):
    restaurant = _staff_restaurant(user); order = db.session.get(Order, order_id)
    if not restaurant or not order or order.restaurant_id != restaurant.id: return _fail("Order not found.", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    target = data.get("status")
    transitions = {"pending": {"confirmed", "cancelled"}, "confirmed": {"preparing", "cancelled"}, "preparing": {"ready_for_pickup"}}
    if target not in transitions.get(order.order_status, set()): return _fail("Invalid status transition.", 409)
    _record_status(order, user, target, data.get("note")); db.session.commit()
    return jsonify({"success": True, "order": _order_json(order)})


@operations_bp.get("/delivery/dashboard")
@role_required("delivery_partner")
def delivery_dashboard(user):
    partner = DeliveryPartner.query.filter_by(user_id=user.id).first()
    if not partner: return _fail("Delivery profile is not configured.", 403)
    available = Order.query.filter_by(order_status="ready_for_pickup", delivery_partner_id=None).count()
    assigned = Order.query.filter_by(delivery_partner_id=partner.id).filter(Order.order_status.notin_(["delivered", "cancelled"])).order_by(Order.placed_at.desc()).all()
    return jsonify({"success": True, "availability_status": partner.availability_status,
        "available_orders": available, "assigned_orders": [_order_json(o) for o in assigned]})


@operations_bp.get("/delivery/orders/available")
@role_required("delivery_partner")
def delivery_available_orders(user):
    partner = DeliveryPartner.query.filter_by(user_id=user.id).first()
    if not partner: return _fail("Delivery profile is not configured.", 403)
    rows = Order.query.filter_by(order_status="ready_for_pickup", delivery_partner_id=None).order_by(Order.placed_at.asc()).limit(100).all()
    return jsonify({"success": True, "orders": [_order_json(o) for o in rows]})


@operations_bp.post("/delivery/orders/<int:order_id>/claim")
@role_required("delivery_partner")
@csrf_protected
def delivery_claim_order(user, order_id):
    partner = DeliveryPartner.query.filter_by(user_id=user.id).first()
    order = db.session.get(Order, order_id)
    if not partner: return _fail("Delivery profile is not configured.", 403)
    if not order or order.order_status != "ready_for_pickup" or order.delivery_partner_id is not None:
        return _fail("This order is no longer available to claim.", 409)
    # Lock the row so two partners cannot both claim the same delivery.
    locked = Order.query.filter_by(id=order_id, order_status="ready_for_pickup", delivery_partner_id=None).with_for_update().first()
    if not locked: return _fail("This order is no longer available to claim.", 409)
    locked.delivery_partner_id = partner.id; partner.availability_status = "busy"
    _activity(user.id, "delivery_claimed", f"Delivery partner {partner.id} claimed order {order_id}")
    db.session.commit()
    return jsonify({"success": True, "order": _order_json(locked)})


@operations_bp.patch("/delivery/orders/<int:order_id>/status")
@role_required("delivery_partner")
@csrf_protected
def delivery_update_order(user, order_id):
    partner = DeliveryPartner.query.filter_by(user_id=user.id).first(); order = db.session.get(Order, order_id)
    if not partner or not order or order.delivery_partner_id != partner.id: return _fail("Assigned delivery order not found.", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return _fail("JSON object required.")
    target = data.get("status")
    transitions = {"ready_for_pickup": {"picked_up"}, "picked_up": {"out_for_delivery"}, "out_for_delivery": {"delivered"}}
    if target not in transitions.get(order.order_status, set()): return _fail("Invalid delivery status transition.", 409)
    _record_status(order, user, target, data.get("note"))
    if target == "delivered":
        if order.payment and order.payment.payment_method == "cash_on_delivery":
            order.payment.payment_status = "paid"; order.payment.payment_date = datetime.utcnow()
        partner.availability_status = "available"
    db.session.commit(); return jsonify({"success": True, "order": _order_json(order)})
