"""Phase 2/3: role-based access control, CORS."""

import pytest
from flask import jsonify

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.middleware.auth import login_required, role_required
from tests.conftest import _truncate_all_except_roles, login, make_user
from app.utils import rate_limit


@pytest.fixture()
def rbac_app():
    """An app with throw-away protected routes, registered BEFORE the
    first request (Flask requires that)."""
    application = create_app(TestConfig)
    rate_limit.reset_all()

    @application.get("/_t/admin-only")
    @role_required("super_admin")
    def admin_only(user):
        return jsonify({"ok": True, "who": user.email})

    @application.get("/_t/staff-or-delivery")
    @role_required("staff", "delivery_partner")
    def multi(user):
        return jsonify({"ok": True})

    @application.get("/_t/any-user")
    @login_required
    def any_user(user):
        return jsonify({"ok": True})

    with application.app_context():
        _truncate_all_except_roles()
        yield application
        db.session.remove()


def test_role_required_blocks_anonymous(rbac_app):
    assert rbac_app.test_client().get("/_t/admin-only").status_code == 401


def test_role_required_blocks_wrong_role(rbac_app):
    make_user("cust@example.com", role="customer")
    c = rbac_app.test_client()
    login(c, "cust@example.com")
    r = c.get("/_t/admin-only")
    assert r.status_code == 403
    assert r.get_json()["code"] == "ACCESS_DENIED"


def test_role_required_allows_correct_role(rbac_app):
    make_user("boss@example.com", role="super_admin")
    c = rbac_app.test_client()
    login(c, "boss@example.com", role="super_admin")
    r = c.get("/_t/admin-only")
    assert r.status_code == 200
    assert r.get_json()["who"] == "boss@example.com"


def test_role_required_accepts_any_listed_role(rbac_app):
    for role in ("staff", "delivery_partner"):
        make_user(f"{role}@example.com", role=role)
        c = rbac_app.test_client()
        login(c, f"{role}@example.com", role=role)
        assert c.get("/_t/staff-or-delivery").status_code == 200
    make_user("cust@example.com")
    c = rbac_app.test_client()
    login(c, "cust@example.com")
    assert c.get("/_t/staff-or-delivery").status_code == 403


def test_browser_supplied_role_is_ignored(rbac_app):
    """Role strings in headers, query strings or JSON never grant access."""
    make_user("cust@example.com", role="customer")
    c = rbac_app.test_client()
    login(c, "cust@example.com")
    r = c.get(
        "/_t/admin-only?role=super_admin",
        headers={"X-Role": "super_admin", "Role": "super_admin"},
        json={"role": "super_admin"},
    )
    assert r.status_code == 403


def test_forged_session_user_id_cannot_become_admin(rbac_app):
    """Even if a cookie says user_id=<admin>, no valid signature = no access."""
    make_user("boss@example.com", role="super_admin")
    c = rbac_app.test_client()
    c.set_cookie("session", "forged.value.here")
    assert c.get("/_t/admin-only").status_code == 401


def test_role_change_in_database_takes_effect_immediately(rbac_app):
    user = make_user("boss@example.com", role="super_admin")
    c = rbac_app.test_client()
    login(c, "boss@example.com", role="super_admin")
    assert c.get("/_t/admin-only").status_code == 200

    from app.models import Role
    user.role_id = Role.query.filter_by(name="customer").one().id
    db.session.commit()
    assert c.get("/_t/admin-only").status_code == 403


def test_deactivated_admin_loses_access(rbac_app):
    user = make_user("boss@example.com", role="super_admin")
    c = rbac_app.test_client()
    login(c, "boss@example.com", role="super_admin")
    user.is_active = False
    db.session.commit()
    assert c.get("/_t/admin-only").status_code == 401


# ---------------- CORS ----------------

def test_cors_allows_configured_frontend_with_credentials(client):
    r = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5500"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5500"
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_rejects_unknown_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_rejects_null_origin(client):
    r = client.get("/api/health", headers={"Origin": "null"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_preflight_allows_csrf_header(client):
    r = client.options(
        "/api/auth/logout",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert r.status_code in (200, 204)
    allowed = r.headers.get("Access-Control-Allow-Headers", "").lower()
    assert "x-csrf-token" in allowed


# ---------------- configuration safety ----------------

def test_production_refuses_placeholder_secret_key():
    from app.config import Config

    class ProdConfig(Config):
        ENVIRONMENT = "production"
        SECRET_KEY = "change-this-to-a-random-secret-key"

    with pytest.raises(RuntimeError):
        create_app(ProdConfig)


def test_production_never_exposes_dev_reset_link():
    """Even if EXPOSE_DEV_RESET_LINK were left on, a production
    environment must not return the reset link."""
    from app.config import Config

    class ProdConfig(TestConfig):
        ENVIRONMENT = "production"
        EXPOSE_DEV_RESET_LINK = True   # worst case: flag wrongly left on

    application = create_app(ProdConfig)
    with application.app_context():
        _truncate_all_except_roles()
        make_user("a@example.com")
        r = application.test_client().post(
            "/api/auth/forgot-password", json={"email": "a@example.com"})
        assert r.status_code == 200
        assert "development_reset_url" not in r.get_json()
        db.session.remove()
