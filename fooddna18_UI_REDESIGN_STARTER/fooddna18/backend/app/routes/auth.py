from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    session
)

from ..middleware.auth import (
    csrf_protected,
    get_csrf_token,
    login_required
)
from ..models import AdminApproval, User
from ..services.auth_service import (
    EMAIL_EXISTS_MESSAGE,
    apply_restaurant_admin,
    authenticate_user,
    create_password_reset_token,
    get_restaurant_admin_application,
    register_customer,
    reset_password
)
from ..utils import rate_limit


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _fail(message, status, code=None):
    body = {"success": False, "error": message}
    if code:
        body["code"] = code
    return jsonify(body), status


def _throttle_key(email):
    safe_email = email.strip().lower() if isinstance(email, str) else ""
    return f"{request.remote_addr}|{safe_email}"


def _is_throttled(email):
    return rate_limit.is_locked(
        _throttle_key(email),
        current_app.config["AUTH_MAX_FAILED_ATTEMPTS"],
        current_app.config["AUTH_LOCKOUT_MINUTES"]
    )


def _too_many_attempts():
    return _fail(
        "Too many failed attempts. Please wait a few minutes "
        "and try again.",
        429,
        "TOO_MANY_ATTEMPTS"
    )


# ---------------------------------------------------------------
# Registration
# ---------------------------------------------------------------

@auth_bp.post("/register")
def register():
    data = _json_body()

    user, error = register_customer(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        password=data.get("password", ""),
        confirm_password=data.get("confirm_password", "")
    )

    if user is None:
        status = 409 if error == EMAIL_EXISTS_MESSAGE else 400
        return _fail(error, status)

    return jsonify(
        {
            "success": True,
            "message": "Customer account created successfully.",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": "customer"
            }
        }
    ), 201


@auth_bp.post("/restaurant-admin/apply")
def restaurant_admin_apply():
    data = _json_body()

    user, error = apply_restaurant_admin(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        password=data.get("password", ""),
        confirm_password=data.get("confirm_password", ""),
        restaurant_name=data.get("restaurant_name", ""),
        restaurant_address=data.get("restaurant_address", ""),
        restaurant_phone=data.get("restaurant_phone"),
        restaurant_email=data.get("restaurant_email")
    )

    if user is None:
        status = 409 if error == EMAIL_EXISTS_MESSAGE else 400
        return _fail(error, status)

    return jsonify(
        {
            "success": True,
            "message": (
                "Restaurant Admin application submitted "
                "and is pending Super Admin approval."
            ),
            "status": "pending"
        }
    ), 201


# ---------------------------------------------------------------
# Login, current user, CSRF, logout
# ---------------------------------------------------------------

@auth_bp.post("/login")
def login():
    data = _json_body()

    email = data.get("email", "")
    password = data.get("password", "")
    selected_role = data.get("role", "")
    remember_me = bool(data.get("remember_me", False))

    if not email or not password or not selected_role:
        return _fail("Email, password and role are required.", 400)

    if _is_throttled(email):
        return _too_many_attempts()

    user, result = authenticate_user(
        email=email,
        password=password,
        selected_role=selected_role,
        remember_me=remember_me
    )

    if user is None:
        # Only wrong credentials count towards the lockout.
        if result["code"] == "INVALID_LOGIN":
            rate_limit.record_failure(
                _throttle_key(email),
                current_app.config["AUTH_LOCKOUT_MINUTES"]
            )

        status_code = 401

        if result["code"] in {
            "ROLE_MISMATCH",
            "ACCOUNT_PENDING",
            "ACCOUNT_REJECTED",
            "ACCOUNT_SUSPENDED",
            "ROLE_NOT_CONFIGURED"
        }:
            status_code = 403

        return _fail(result["message"], status_code, result["code"])

    rate_limit.clear(_throttle_key(email))

    return jsonify(
        {
            "success": True,
            "message": result["message"],
            "csrf_token": get_csrf_token(),
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.name
            }
        }
    ), 200


@auth_bp.get("/me")
@login_required
def current_user(user):
    return jsonify(
        {
            "success": True,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.name,
                "account_status": user.account_status,
                "approval_status": user.approval_status,
                "is_active": user.is_active
            }
        }
    )


@auth_bp.get("/csrf")
@login_required
def csrf_token(user):
    return jsonify({"success": True, "csrf_token": get_csrf_token()})


@auth_bp.post("/logout")
@login_required
@csrf_protected
def logout(user):
    session.clear()

    return jsonify(
        {"success": True, "message": "Logged out successfully."}
    )


# ---------------------------------------------------------------
# Restaurant Admin application status
# ---------------------------------------------------------------

@auth_bp.get("/application-status")
@login_required
def application_status(user):
    """For a logged-in user who has a Restaurant Admin application."""
    approval = AdminApproval.query.filter_by(
        user_id=user.id,
        approval_type="restaurant_admin"
    ).order_by(AdminApproval.id.desc()).first()

    if approval is None:
        return _fail("Application record not found.", 404)

    return jsonify(
        {
            "success": True,
            "status": approval.status,
            "account_status": user.account_status,
            "approval_status": user.approval_status,
            "remarks": approval.remarks
        }
    )


@auth_bp.post("/application-status/check")
def application_status_check():
    """
    For applicants who are NOT allowed to log in yet (pending or
    rejected). They prove who they are with email + password and
    see only the status of their own application.
    """
    data = _json_body()
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return _fail("Email and password are required.", 400)

    if _is_throttled(email):
        return _too_many_attempts()

    info, error = get_restaurant_admin_application(email, password)

    if info is None:
        rate_limit.record_failure(
            _throttle_key(email),
            current_app.config["AUTH_LOCKOUT_MINUTES"]
        )
        status = 404 if "No Restaurant Admin" in error else 401
        return _fail(error, status)

    rate_limit.clear(_throttle_key(email))

    return jsonify({"success": True, **info})


# ---------------------------------------------------------------
# Password recovery
# ---------------------------------------------------------------

@auth_bp.post("/forgot-password")
def forgot_password():
    data = _json_body()
    raw_email = data.get("email", "")

    # Always return the same public response so account existence
    # is not revealed.
    response = {
        "success": True,
        "message": (
            "If an account exists for this email, "
            "password reset instructions have been generated."
        )
    }

    if not isinstance(raw_email, str) or not raw_email.strip():
        return _fail("Email is required.", 400)

    user = User.query.filter_by(
        email=raw_email.strip().lower()
    ).first()

    if user is None or not user.is_active:
        return jsonify(response)

    raw_token = create_password_reset_token(user)

    # DEVELOPMENT ONLY: there is no email service, so the link is
    # returned here. In production this flag is False and the link
    # must be delivered by email instead.
    if (
        current_app.config["EXPOSE_DEV_RESET_LINK"]
        and current_app.config["ENVIRONMENT"] == "development"
    ):
        response["development_reset_url"] = (
            f"{current_app.config['FRONTEND_URL']}"
            f"/reset-password.html?token={raw_token}"
        )

    return jsonify(response)


@auth_bp.post("/reset-password")
def reset_password_route():
    data = _json_body()

    success, error = reset_password(
        raw_token=data.get("token", ""),
        new_password=data.get("password", ""),
        confirm_password=data.get("confirm_password", "")
    )

    if not success:
        return _fail(error, 400)

    return jsonify(
        {
            "success": True,
            "message": (
                "Password reset successfully. You can now log in."
            )
        }
    )
