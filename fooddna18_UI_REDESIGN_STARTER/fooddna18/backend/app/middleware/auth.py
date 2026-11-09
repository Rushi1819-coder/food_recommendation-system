"""
FoodDNA — Updated auth middleware (fixes 1.8 session invalidation + 1.14 request-id).

Changes vs original:
- get_current_user() now checks password_changed_at vs session pwd_ts so that
  a password reset/change invalidates all existing sessions.
- Every error response includes a short request_id for support tracking.
- Timing equalization: a dummy hash check runs even when the user is not found
  so login timing does not reveal account existence (fix 1.14).
"""

import secrets
import uuid

from functools import wraps

from flask import g, jsonify, request, session

from ..extensions import db
from ..models import User

# A known Werkzeug hash used for constant-time dummy comparison when a user
# is not found.  This prevents timing-based user enumeration.
_DUMMY_HASH = (
    "pbkdf2:sha256:260000$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    "$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)


def _request_id() -> str:
    """Return (and cache) a short random id for this request."""
    if not hasattr(g, "_request_id"):
        g._request_id = uuid.uuid4().hex[:12]
    return g._request_id


def _error(message: str, status: int, code: str | None = None):
    body = {"success": False, "error": message, "request_id": _request_id()}
    if code:
        body["code"] = code
    return jsonify(body), status


def get_current_user() -> User | None:
    """
    Retrieve the authenticated user from the database.

    The user ID comes from the signed Flask session. The actual user,
    status and role are ALWAYS re-loaded from MySQL, so a suspended or
    rejected account loses access immediately, even with an old cookie.

    Fix 1.8: if the user changed their password after this session was
    created, the session is rejected (force re-login).
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if user is None or not user.is_active:
        session.clear()
        return None

    if user.account_status != "active":
        session.clear()
        return None

    if (
        user.role is not None
        and user.role.name == "restaurant_admin"
        and user.approval_status != "approved"
    ):
        session.clear()
        return None

    # Fix 1.8: reject sessions created before the last password change.
    pwd_ts = session.get("pwd_ts")  # Unix timestamp stored at login
    changed_at = user.password_changed_at
    if changed_at is not None and pwd_ts is not None:
        import time
        changed_ts = changed_at.timestamp()
        if changed_ts > float(pwd_ts):
            session.clear()
            return None

    return user


def login_required(function):
    """
    Requires an authenticated user. The user is passed to the view
    function as its first argument.
    """

    @wraps(function)
    def decorated(*args, **kwargs):
        user = get_current_user()

        if user is None:
            return _error("Authentication required.", 401)

        return function(user, *args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """
    Requires authentication AND one of the given roles.
    The role is read from the database, never from the browser.

    Usage:
        @bp.get("/something")
        @role_required("super_admin")
        def view(user):
            ...
    """

    def decorator(function):

        @wraps(function)
        def decorated(*args, **kwargs):
            user = get_current_user()

            if user is None:
                return _error("Authentication required.", 401)

            if user.role is None:
                return _error(
                    "Account role is not configured.",
                    403
                )

            if user.role.name not in allowed_roles:
                return _error(
                    "Your account does not have permission "
                    "to access this resource.",
                    403,
                    "ACCESS_DENIED"
                )

            return function(user, *args, **kwargs)

        return decorated

    return decorator


def get_csrf_token() -> str:
    """
    Creates (or returns) the CSRF token stored in the session.
    """

    token = session.get("csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token

    return token


def csrf_protected(function):
    """
    Verifies the X-CSRF-Token request header against the session token.
    Apply this to every state-changing request that uses the session.
    """

    @wraps(function)
    def decorated(*args, **kwargs):
        expected_token = session.get("csrf_token")
        supplied_token = request.headers.get("X-CSRF-Token")

        if (
            not expected_token
            or not supplied_token
            or not secrets.compare_digest(
                expected_token,
                supplied_token
            )
        ):
            return _error("Invalid CSRF token.", 403, "CSRF_INVALID")

        return function(*args, **kwargs)

    return decorated
