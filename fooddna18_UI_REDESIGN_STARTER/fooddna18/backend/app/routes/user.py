"""
FoodDNA - User profile, addresses, and account management routes.
Provides REST endpoints for customer profile, saved delivery addresses,
and password change.
"""

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..middleware.auth import csrf_protected, login_required
from ..models import User, UserAddress
from ..utils.timeutil import utcnow
from ..utils.validation import validate_full_name, validate_password

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _address_json(addr):
    return {
        "id": addr.id,
        "label": addr.label,
        "full_address": addr.full_address,
        "is_default": bool(addr.is_default),
        "created_at": addr.created_at.isoformat() if addr.created_at else None,
    }


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@user_bp.get("/profile")
@login_required
def get_profile(user):
    addresses = (
        UserAddress.query.filter_by(user_id=user.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
        .all()
    )
    return jsonify({
        "success": True,
        "profile": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.name if user.role else None,
            "account_status": user.account_status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "addresses": [_address_json(a) for a in addresses],
        }
    })


@user_bp.patch("/profile")
@login_required
@csrf_protected
def update_profile(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("JSON body required.")

    if "full_name" in data:
        full_name = str(data.get("full_name") or "")
        valid, err = validate_full_name(full_name)
        if not valid:
            return _fail(err)
        user.full_name = full_name.strip()

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.name if user.role else None,
        }
    })


@user_bp.post("/change-password")
@login_required
@csrf_protected
def change_password(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("JSON body required.")

    current_password = str(data.get("current_password") or "")
    new_password = str(data.get("new_password") or "")
    confirm_password = str(data.get("confirm_password") or "")

    if not current_password or not new_password or not confirm_password:
        return _fail("All password fields are required.")

    if not check_password_hash(user.password_hash, current_password):
        return _fail("Current password is incorrect.", 401)

    if new_password != confirm_password:
        return _fail("New password and confirmation do not match.")

    valid, err = validate_password(new_password)
    if not valid:
        return _fail(err)

    user.password_hash = generate_password_hash(new_password)
    user.password_changed_at = utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Password changed successfully."
    })


# ---------------------------------------------------------------------------
# Saved Addresses (Stage 5 / Screen 7 & 15)
# ---------------------------------------------------------------------------

@user_bp.get("/addresses")
@login_required
def list_addresses(user):
    addresses = (
        UserAddress.query.filter_by(user_id=user.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
        .all()
    )
    return jsonify({
        "success": True,
        "addresses": [_address_json(a) for a in addresses]
    })


@user_bp.post("/addresses")
@login_required
@csrf_protected
def add_address(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _fail("JSON body required.")

    label = str(data.get("label") or "Home").strip()[:80]
    full_address = str(data.get("full_address") or "").strip()
    is_default = bool(data.get("is_default", False))

    if not full_address:
        return _fail("full_address is required.")
    if len(full_address) > 1000:
        return _fail("full_address is too long (maximum 1000 characters).")

    count = UserAddress.query.filter_by(user_id=user.id).count()
    if count >= 10:
        return _fail("Address limit reached (maximum 10 saved addresses).")

    # If this is the user's first address, make it default automatically
    if count == 0:
        is_default = True

    if is_default:
        UserAddress.query.filter_by(user_id=user.id).update({"is_default": False})

    new_addr = UserAddress(
        user_id=user.id,
        label=label or "Home",
        full_address=full_address,
        is_default=is_default,
    )
    db.session.add(new_addr)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Address added successfully.",
        "address": _address_json(new_addr)
    }), 201


@user_bp.patch("/addresses/<int:address_id>/default")
@login_required
@csrf_protected
def set_default_address(user, address_id):
    addr = UserAddress.query.filter_by(id=address_id, user_id=user.id).first()
    if not addr:
        return _fail("Address not found.", 404)

    UserAddress.query.filter_by(user_id=user.id).update({"is_default": False})
    addr.is_default = True
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Default address updated.",
        "address": _address_json(addr)
    })


@user_bp.delete("/addresses/<int:address_id>")
@login_required
@csrf_protected
def delete_address(user, address_id):
    addr = UserAddress.query.filter_by(id=address_id, user_id=user.id).first()
    if not addr:
        return _fail("Address not found.", 404)

    was_default = addr.is_default
    db.session.delete(addr)
    db.session.flush()

    # If we deleted the default, set another address as default if one exists
    if was_default:
        next_addr = (
            UserAddress.query.filter_by(user_id=user.id)
            .order_by(UserAddress.id.desc())
            .first()
        )
        if next_addr:
            next_addr.is_default = True

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Address deleted successfully."
    })
