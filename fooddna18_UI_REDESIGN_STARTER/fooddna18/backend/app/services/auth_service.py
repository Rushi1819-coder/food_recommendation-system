"""
FoodDNA — Auth service.
Fixes applied:
  1.1  — iso_utc() used for all datetime serialisation
  1.8  — pwd_ts stored in session at login; password_changed_at set on reset
  1.14 — dummy hash check when user not found (timing equalization)
  general — datetime.utcnow() replaced with utcnow() from timeutil
"""

import hashlib
import secrets
import time

from flask import current_app, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from ..extensions import db
from ..models import (
    AdminApproval,
    PasswordResetToken,
    Restaurant,
    RestaurantAdmin,
    Role,
    User,
)
from ..utils.timeutil import iso_utc, utcnow
from ..utils.validation import (
    validate_confirm_password,
    validate_email,
    validate_full_name,
    validate_password,
)


EMAIL_EXISTS_MESSAGE = "An account with this email already exists."

# Used for timing equalization when the user is not found.
# This is a valid Werkzeug-format hash that will fail against any real password,
# but takes the same time to check as a real hash.
_DUMMY_HASH = generate_password_hash("__dummy_password_never_matches__")


def get_role(role_name: str) -> Role | None:
    return Role.query.filter_by(name=role_name).first()


def register_customer(
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
):
    valid, message = validate_full_name(full_name)
    if not valid:
        return None, message

    valid, message = validate_email(email)
    if not valid:
        return None, message

    valid, message = validate_password(password)
    if not valid:
        return None, message

    valid, message = validate_confirm_password(password, confirm_password)
    if not valid:
        return None, message

    email = email.strip().lower()
    full_name = full_name.strip()

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return None, EMAIL_EXISTS_MESSAGE

    role = get_role("customer")
    if role is None:
        return None, "Customer role is not configured."

    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role_id=role.id,
        account_status="active",
        approval_status="not_required",
        is_active=True,
    )

    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, EMAIL_EXISTS_MESSAGE

    return user, ""


def apply_restaurant_admin(
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    restaurant_name: str,
    restaurant_address: str,
    restaurant_phone=None,
    restaurant_email=None,
):
    valid, message = validate_full_name(full_name)
    if not valid:
        return None, message

    valid, message = validate_email(email)
    if not valid:
        return None, message

    valid, message = validate_password(password)
    if not valid:
        return None, message

    valid, message = validate_confirm_password(password, confirm_password)
    if not valid:
        return None, message

    for value in (restaurant_name, restaurant_address):
        if not isinstance(value, str):
            return None, "Restaurant name and address are required."

    for optional in (restaurant_phone, restaurant_email):
        if optional is not None and not isinstance(optional, str):
            return None, "Restaurant phone and email must be text."

    if len(restaurant_name.strip()) > 150:
        return None, "Restaurant name must be 150 characters or fewer."

    if restaurant_phone and len(restaurant_phone.strip()) > 20:
        return None, "Restaurant phone must be 20 characters or fewer."

    if not restaurant_name or not restaurant_name.strip():
        return None, "Restaurant name is required."

    if not restaurant_address or not restaurant_address.strip():
        return None, "Restaurant address is required."

    email = email.strip().lower()

    if User.query.filter_by(email=email).first():
        return None, EMAIL_EXISTS_MESSAGE

    role = get_role("restaurant_admin")
    if role is None:
        return None, "Restaurant Admin role is not configured."

    user = User(
        full_name=full_name.strip(),
        email=email,
        password_hash=generate_password_hash(password),
        role_id=role.id,
        account_status="pending",
        approval_status="pending",
        is_active=True,
    )

    db.session.add(user)
    db.session.flush()

    restaurant = Restaurant(
        name=restaurant_name.strip(),
        address=restaurant_address.strip(),
        phone=restaurant_phone.strip() if restaurant_phone else None,
        email=restaurant_email.strip().lower() if restaurant_email else None,
        status="pending",
        capacity_status="normal",
    )

    db.session.add(restaurant)
    db.session.flush()

    restaurant_admin = RestaurantAdmin(
        user_id=user.id,
        restaurant_id=restaurant.id,
    )
    db.session.add(restaurant_admin)

    approval = AdminApproval(
        user_id=user.id,
        restaurant_id=restaurant.id,
        approval_type="restaurant_admin",
        status="pending",
    )
    db.session.add(approval)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, EMAIL_EXISTS_MESSAGE

    return user, ""


def authenticate_user(
    email: str,
    password: str,
    selected_role: str,
    remember_me: bool = False,
):
    """
    Authenticate a user. Includes timing equalization (fix 1.14):
    a dummy hash check always runs when the user is not found so the
    response time does not reveal whether the email exists.
    """
    if not isinstance(email, str) or not isinstance(password, str):
        # Still run dummy check for timing
        check_password_hash(_DUMMY_HASH, "__irrelevant__")
        return None, {
            "status": "error",
            "code": "INVALID_LOGIN",
            "message": "Invalid email or password.",
        }

    email = email.strip().lower()

    user = User.query.filter_by(email=email).first()

    if user is None:
        # Timing equalization: run a real bcrypt check so the response
        # time is indistinguishable from a failed password check.
        check_password_hash(_DUMMY_HASH, password)
        return None, {
            "status": "error",
            "code": "INVALID_LOGIN",
            "message": "Invalid email or password.",
        }

    if not check_password_hash(user.password_hash, password):
        return None, {
            "status": "error",
            "code": "INVALID_LOGIN",
            "message": "Invalid email or password.",
        }

    if user.role is None:
        return None, {
            "status": "error",
            "code": "ROLE_NOT_CONFIGURED",
            "message": "Your account role is not configured.",
        }

    # CRITICAL: The browser-selected role is checked against the DB.
    if selected_role != user.role.name:
        return None, {
            "status": "error",
            "code": "ROLE_MISMATCH",
            "message": (
                "Your account does not have permission "
                "to access this portal."
            ),
        }

    if not user.is_active:
        return None, {
            "status": "error",
            "code": "ACCOUNT_SUSPENDED",
            "message": "Your account is suspended.",
        }

    if user.account_status == "pending":
        return None, {
            "status": "error",
            "code": "ACCOUNT_PENDING",
            "message": "Your account is pending approval.",
        }

    if user.account_status == "rejected":
        return None, {
            "status": "error",
            "code": "ACCOUNT_REJECTED",
            "message": "Your account application was rejected.",
        }

    if user.account_status == "suspended":
        return None, {
            "status": "error",
            "code": "ACCOUNT_SUSPENDED",
            "message": "Your account is suspended.",
        }

    if (
        user.role.name == "restaurant_admin"
        and user.approval_status != "approved"
    ):
        return None, {
            "status": "error",
            "code": "ACCOUNT_PENDING",
            "message": (
                "Your Restaurant Admin application "
                "is still pending approval."
            ),
        }

    session.clear()
    session["user_id"] = user.id
    session.permanent = bool(remember_me)

    # Fix 1.8: store the time at which the session was created so that
    # a subsequent password change can invalidate it.
    session["pwd_ts"] = time.time()

    user.last_login_at = utcnow()
    db.session.commit()

    return user, {
        "status": "success",
        "code": "LOGIN_SUCCESS",
        "message": "Login successful.",
    }


def create_password_reset_token(user: User) -> str:
    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expiry = utcnow()
    from datetime import timedelta
    expiry = expiry.replace()
    expiry = utcnow() + timedelta(
        minutes=current_app.config["PASSWORD_RESET_EXPIRY_MINUTES"]
    )

    # Invalidate old tokens.
    PasswordResetToken.query.filter_by(
        user_id=user.id,
        used_at=None,
    ).update({"used_at": utcnow()})

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expiry,
    )
    db.session.add(reset_token)
    db.session.commit()

    return raw_token


def reset_password(
    raw_token: str,
    new_password: str,
    confirm_password: str,
):
    if not raw_token or not isinstance(raw_token, str):
        return False, "Reset token is required."

    valid, message = validate_password(new_password)
    if not valid:
        return False, message

    valid, message = validate_confirm_password(new_password, confirm_password)
    if not valid:
        return False, message

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    reset_token = PasswordResetToken.query.filter_by(
        token_hash=token_hash
    ).first()

    if reset_token is None:
        return False, "Invalid password reset token."

    if reset_token.used_at is not None:
        return False, "This reset token has already been used."

    now = utcnow()
    if now > reset_token.expires_at:
        return False, "This reset token has expired."

    user = db.session.get(User, reset_token.user_id)
    if user is None:
        return False, "User account could not be found."

    # Atomically claim the token. Only one concurrent reset wins.
    claimed = PasswordResetToken.query.filter_by(
        id=reset_token.id,
        used_at=None,
    ).update({"used_at": now})

    if claimed != 1:
        db.session.rollback()
        return False, "This reset token has already been used."

    user.password_hash = generate_password_hash(new_password)

    # Fix 1.8: record the change time so existing sessions are invalidated.
    user.password_changed_at = now

    db.session.commit()
    return True, ""


def get_restaurant_admin_application(email: str, password: str):
    """
    Lets an applicant check their application status with their
    email + password, WITHOUT needing a login session.
    """
    generic_error = "Invalid email or password."

    if not isinstance(email, str) or not isinstance(password, str):
        return None, generic_error

    user = User.query.filter_by(email=email.strip().lower()).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return None, generic_error

    approval = AdminApproval.query.filter_by(
        user_id=user.id,
        approval_type="restaurant_admin",
    ).order_by(AdminApproval.id.desc()).first()

    if approval is None:
        return None, "No Restaurant Admin application found for this account."

    restaurant = (
        db.session.get(Restaurant, approval.restaurant_id)
        if approval.restaurant_id
        else None
    )

    return {
        "status": approval.status,
        "remarks": approval.remarks,
        "restaurant_name": restaurant.name if restaurant else None,
        "submitted_at": iso_utc(approval.created_at),
        "reviewed_at": iso_utc(approval.reviewed_at),
    }, None
