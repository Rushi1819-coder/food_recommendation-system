"""Phase 3: customer authentication, sessions, CSRF, password reset,
Restaurant Admin application and status."""

from datetime import datetime, timedelta
import hashlib

from app.extensions import db
from app.models import (
    AdminApproval, PasswordResetToken, Restaurant, RestaurantAdmin, User,
)
from tests.conftest import STRONG_PASSWORD, csrf_headers, login, make_user

REGISTER = {
    "full_name": "Asha Kumar",
    "email": "asha@gmail.com",
    "password": STRONG_PASSWORD,
    "confirm_password": STRONG_PASSWORD,
}


# ---------------- registration ----------------

def test_register_customer_success_and_hashed_password(client):
    r = client.post("/api/auth/register", json=REGISTER)
    assert r.status_code == 201
    body = r.get_json()
    assert body["user"]["role"] == "customer"
    assert "password" not in str(body).lower().replace("password_", "")

    user = User.query.filter_by(email="asha@gmail.com").first()
    assert user is not None
    assert user.password_hash != STRONG_PASSWORD
    assert STRONG_PASSWORD not in user.password_hash
    assert user.role.name == "customer"
    assert user.account_status == "active"


def test_register_email_is_normalised(client):
    data = dict(REGISTER, email="  ASHA@GMAIL.COM ")
    assert client.post("/api/auth/register", json=data).status_code == 201
    assert User.query.filter_by(email="asha@gmail.com").count() == 1


def test_register_duplicate_email_is_409(client):
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201
    r = client.post("/api/auth/register", json=REGISTER)
    assert r.status_code == 409
    assert "already exists" in r.get_json()["error"]
    assert User.query.count() == 1


def test_register_duplicate_email_different_case_is_409(client):
    client.post("/api/auth/register", json=REGISTER)
    r = client.post("/api/auth/register", json=dict(REGISTER, email="ASHA@GMAIL.COM"))
    assert r.status_code == 409


def test_register_rejects_bad_input(client):
    cases = {
        "weak password": dict(REGISTER, password="abc", confirm_password="abc"),
        "mismatch": dict(REGISTER, confirm_password="Different1!"),
        "bad email": dict(REGISTER, email="not-an-email"),
        "empty name": dict(REGISTER, full_name="   "),
        "digits in name": dict(REGISTER, full_name="Asha 123"),
        "missing fields": {},
    }
    for label, payload in cases.items():
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400, label
        assert r.get_json()["success"] is False, label
    assert User.query.count() == 0


def test_register_ignores_role_supplied_by_browser(client):
    """A user must not be able to register as an administrator."""
    data = dict(REGISTER, role="super_admin", role_id=5)
    r = client.post("/api/auth/register", json=data)
    assert r.status_code == 201
    assert User.query.filter_by(email="asha@gmail.com").first().role.name == "customer"


def test_register_non_json_body_is_400(client):
    r = client.post("/api/auth/register", data="hello", content_type="text/plain")
    assert r.status_code == 400


# ---------------- login / session ----------------

def test_login_success_sets_session_and_returns_csrf(client):
    make_user("a@example.com")
    r = login(client, "a@example.com")
    assert r.status_code == 200
    body = r.get_json()
    assert body["user"]["role"] == "customer"
    assert body["csrf_token"]
    assert client.get("/api/auth/me").status_code == 200


def test_login_response_never_contains_password_hash(client):
    make_user("a@example.com")
    text = login(client, "a@example.com").get_data(as_text=True)
    assert "pbkdf2" not in text and "scrypt" not in text
    assert "password_hash" not in text


def test_login_invalid_credentials_are_generic_401(client):
    make_user("a@example.com")
    wrong_pw = login(client, "a@example.com", password="Wrong1234!")
    no_user = login(client, "ghost@example.com")
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.get_json()["error"] == no_user.get_json()["error"]


def test_login_requires_all_fields(client):
    r = client.post("/api/auth/login", json={"email": "a@example.com"})
    assert r.status_code == 400


def test_login_role_mismatch_is_403(client):
    make_user("a@example.com", role="customer")
    r = login(client, "a@example.com", role="super_admin")
    assert r.status_code == 403
    assert r.get_json()["code"] == "ROLE_MISMATCH"
    assert client.get("/api/auth/me").status_code == 401


def test_login_inactive_account_blocked(client):
    make_user("a@example.com", is_active=False)
    r = login(client, "a@example.com")
    assert r.status_code == 403
    assert r.get_json()["code"] == "ACCOUNT_SUSPENDED"


def test_login_suspended_status_blocked(client):
    make_user("a@example.com", account_status="suspended")
    assert login(client, "a@example.com").status_code == 403


def test_login_non_string_values_do_not_crash(client):
    make_user("a@example.com")
    r = client.post(
        "/api/auth/login",
        json={"email": ["x"], "password": {"a": 1}, "role": "customer"},
    )
    assert r.status_code == 401


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_only_safe_fields(client):
    make_user("a@example.com")
    login(client, "a@example.com")
    user = client.get("/api/auth/me").get_json()["user"]
    assert set(user) == {
        "id", "full_name", "email", "role",
        "account_status", "approval_status", "is_active",
    }


def test_session_dies_when_account_is_suspended_after_login(client, app):
    u = make_user("a@example.com")
    login(client, "a@example.com")
    assert client.get("/api/auth/me").status_code == 200
    u.is_active = False
    db.session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_session_dies_when_account_status_changes_after_login(client):
    u = make_user("a@example.com")
    login(client, "a@example.com")
    u.account_status = "suspended"
    db.session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_login_throttle_after_repeated_failures(client):
    make_user("a@example.com")
    for _ in range(5):
        assert login(client, "a@example.com", password="Wrong1234!").status_code == 401
    r = login(client, "a@example.com")  # even the CORRECT password
    assert r.status_code == 429
    assert r.get_json()["code"] == "TOO_MANY_ATTEMPTS"


def test_successful_login_clears_failure_count(client):
    make_user("a@example.com")
    for _ in range(3):
        login(client, "a@example.com", password="Wrong1234!")
    assert login(client, "a@example.com").status_code == 200
    for _ in range(3):
        login(client, "a@example.com", password="Wrong1234!")
    assert login(client, "a@example.com").status_code == 200


# ---------------- CSRF / logout ----------------

def test_logout_requires_login(client):
    assert client.post("/api/auth/logout").status_code == 401


def test_logout_without_csrf_is_rejected(client):
    make_user("a@example.com")
    login(client, "a@example.com")
    r = client.post("/api/auth/logout")
    assert r.status_code == 403
    assert client.get("/api/auth/me").status_code == 200  # still logged in


def test_logout_with_wrong_csrf_is_rejected(client):
    make_user("a@example.com")
    login(client, "a@example.com")
    r = client.post("/api/auth/logout", headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403


def test_logout_with_csrf_ends_session(client):
    make_user("a@example.com")
    login(client, "a@example.com")
    r = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/csrf").status_code == 401


def test_csrf_token_from_other_session_is_rejected(client, app):
    make_user("a@example.com")
    make_user("b@example.com")
    login(client, "a@example.com")
    other = app.test_client()
    login(other, "b@example.com")
    other_token = csrf_headers(other)
    r = client.post("/api/auth/logout", headers=other_token)
    assert r.status_code == 403


# ---------------- password reset ----------------

def _request_reset(client, email="a@example.com"):
    r = client.post("/api/auth/forgot-password", json={"email": email})
    return r


def _token_from(response):
    url = response.get_json()["development_reset_url"]
    assert "/reset-password.html?token=" in url
    return url.split("token=")[1]


def test_forgot_password_does_not_crash_and_returns_dev_link(client):
    make_user("a@example.com")
    r = _request_reset(client)
    assert r.status_code == 200
    assert _token_from(r)


def test_forgot_password_unknown_email_gives_same_message(client):
    make_user("a@example.com")
    known = _request_reset(client).get_json()
    unknown = _request_reset(client, "ghost@example.com").get_json()
    assert known["message"] == unknown["message"]
    assert "development_reset_url" not in unknown


def test_forgot_password_requires_email(client):
    assert client.post("/api/auth/forgot-password", json={}).status_code == 400
    assert client.post("/api/auth/forgot-password", json={"email": 5}).status_code == 400


def test_forgot_password_inactive_user_gets_no_token(client):
    make_user("a@example.com", is_active=False)
    r = _request_reset(client)
    assert r.status_code == 200
    assert "development_reset_url" not in r.get_json()
    assert PasswordResetToken.query.count() == 0


def test_reset_token_is_stored_only_as_hash(client):
    make_user("a@example.com")
    token = _token_from(_request_reset(client))
    row = PasswordResetToken.query.one()
    assert row.token_hash != token
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in row.token_hash


def test_full_password_reset_flow_then_login_with_new_password(client):
    make_user("a@example.com")
    token = _token_from(_request_reset(client))
    new_pw = "NewPassw0rd#"

    r = client.post("/api/auth/reset-password", json={
        "token": token, "password": new_pw, "confirm_password": new_pw})
    assert r.status_code == 200

    assert login(client, "a@example.com", password=STRONG_PASSWORD).status_code == 401
    assert login(client, "a@example.com", password=new_pw).status_code == 200


def test_reset_token_cannot_be_reused(client):
    make_user("a@example.com")
    token = _token_from(_request_reset(client))
    payload = {"token": token, "password": "NewPassw0rd#",
               "confirm_password": "NewPassw0rd#"}
    assert client.post("/api/auth/reset-password", json=payload).status_code == 200
    r = client.post("/api/auth/reset-password", json=dict(
        payload, password="Another1$pass", confirm_password="Another1$pass"))
    assert r.status_code == 400
    assert "already been used" in r.get_json()["error"]
    # password must still be the first new one
    assert login(client, "a@example.com", password="NewPassw0rd#").status_code == 200


def test_expired_reset_token_is_rejected(client):
    make_user("a@example.com")
    token = _token_from(_request_reset(client))
    row = PasswordResetToken.query.one()
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()
    r = client.post("/api/auth/reset-password", json={
        "token": token, "password": "NewPassw0rd#",
        "confirm_password": "NewPassw0rd#"})
    assert r.status_code == 400
    assert "expired" in r.get_json()["error"]
    assert login(client, "a@example.com", password=STRONG_PASSWORD).status_code == 200


def test_invalid_reset_token_is_rejected(client):
    r = client.post("/api/auth/reset-password", json={
        "token": "totally-made-up", "password": "NewPassw0rd#",
        "confirm_password": "NewPassw0rd#"})
    assert r.status_code == 400


def test_reset_rejects_weak_or_mismatched_password(client):
    make_user("a@example.com")
    token = _token_from(_request_reset(client))
    weak = client.post("/api/auth/reset-password", json={
        "token": token, "password": "abc", "confirm_password": "abc"})
    mismatch = client.post("/api/auth/reset-password", json={
        "token": token, "password": "NewPassw0rd#", "confirm_password": "Nope"})
    assert weak.status_code == mismatch.status_code == 400
    # the failed attempts must not burn the token
    ok = client.post("/api/auth/reset-password", json={
        "token": token, "password": "NewPassw0rd#",
        "confirm_password": "NewPassw0rd#"})
    assert ok.status_code == 200


def test_new_reset_request_invalidates_the_previous_token(client):
    make_user("a@example.com")
    old = _token_from(_request_reset(client))
    new = _token_from(_request_reset(client))
    r_old = client.post("/api/auth/reset-password", json={
        "token": old, "password": "NewPassw0rd#", "confirm_password": "NewPassw0rd#"})
    assert r_old.status_code == 400
    r_new = client.post("/api/auth/reset-password", json={
        "token": new, "password": "NewPassw0rd#", "confirm_password": "NewPassw0rd#"})
    assert r_new.status_code == 200


def test_dev_reset_link_hidden_when_not_development(app):
    app.config["EXPOSE_DEV_RESET_LINK"] = False
    c = app.test_client()
    make_user("a@example.com")
    r = c.post("/api/auth/forgot-password", json={"email": "a@example.com"})
    assert r.status_code == 200
    assert "development_reset_url" not in r.get_json()
    assert PasswordResetToken.query.count() == 1  # token still created


# ---------------- restaurant admin application ----------------

APPLY = {
    "full_name": "Rita Owner",
    "email": "rita@gmail.com",
    "password": STRONG_PASSWORD,
    "confirm_password": STRONG_PASSWORD,
    "restaurant_name": "Rita's Kitchen",
    "restaurant_address": "1 Main Road",
    "restaurant_phone": "9876543210",
    "restaurant_email": "kitchen@example.com",
}


def test_restaurant_admin_apply_creates_linked_pending_records(client):
    r = client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    assert r.status_code == 201
    assert r.get_json()["status"] == "pending"

    user = User.query.filter_by(email="rita@gmail.com").one()
    assert user.role.name == "restaurant_admin"
    assert user.account_status == "pending"
    assert user.approval_status == "pending"

    restaurant = Restaurant.query.one()
    assert restaurant.status == "pending"
    link = RestaurantAdmin.query.one()
    assert (link.user_id, link.restaurant_id) == (user.id, restaurant.id)
    approval = AdminApproval.query.one()
    assert approval.status == "pending" and approval.reviewed_by is None


def test_restaurant_admin_apply_validation(client):
    for label, payload in {
        "no restaurant name": dict(APPLY, restaurant_name=""),
        "no address": dict(APPLY, restaurant_address=" "),
        "weak password": dict(APPLY, password="x", confirm_password="x"),
        "name not text": dict(APPLY, restaurant_name=123),
        "phone too long": dict(APPLY, restaurant_phone="1" * 30),
        "punctuation in applicant name": dict(APPLY, full_name="Rita-Owner"),
        "digits in applicant name": dict(APPLY, full_name="Rita 123"),
        "non-Gmail account email": dict(APPLY, email="rita@yahoo.com"),
    }.items():
        r = client.post("/api/auth/restaurant-admin/apply", json=payload)
        assert r.status_code == 400, label
    assert User.query.count() == 0 and Restaurant.query.count() == 0


def test_restaurant_admin_apply_duplicate_email_is_409_and_leaves_no_orphans(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    r = client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    assert r.status_code == 409
    assert Restaurant.query.count() == 1  # no orphan restaurant


def test_pending_restaurant_admin_cannot_log_in(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    r = login(client, "rita@gmail.com", role="restaurant_admin")
    assert r.status_code == 403
    assert r.get_json()["code"] == "ACCOUNT_PENDING"
    assert client.get("/api/auth/me").status_code == 401


def test_rejected_restaurant_admin_cannot_log_in(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    user = User.query.filter_by(email="rita@gmail.com").one()
    user.account_status = "rejected"
    user.approval_status = "rejected"
    db.session.commit()
    r = login(client, "rita@gmail.com", role="restaurant_admin")
    assert r.status_code == 403
    assert r.get_json()["code"] == "ACCOUNT_REJECTED"


def test_approved_restaurant_admin_can_log_in(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    user = User.query.filter_by(email="rita@gmail.com").one()
    user.account_status = "active"
    user.approval_status = "approved"
    db.session.commit()
    assert login(client, "rita@gmail.com", role="restaurant_admin").status_code == 200


def test_restaurant_admin_with_active_status_but_unapproved_is_blocked(client):
    """Defence in depth: account_status alone must not be enough."""
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    user = User.query.filter_by(email="rita@gmail.com").one()
    user.account_status = "active"          # approval_status stays "pending"
    db.session.commit()
    r = login(client, "rita@gmail.com", role="restaurant_admin")
    assert r.status_code == 403


# ---------------- application status ----------------

def test_application_status_logged_in_requires_login(client):
    assert client.get("/api/auth/application-status").status_code == 401


def test_application_status_logged_in_for_customer_is_404(client):
    make_user("a@example.com")
    login(client, "a@example.com")
    assert client.get("/api/auth/application-status").status_code == 404


def test_pending_applicant_can_check_status_with_credentials(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    r = client.post("/api/auth/application-status/check", json={
        "email": "rita@gmail.com", "password": STRONG_PASSWORD})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "pending"
    assert body["restaurant_name"] == "Rita's Kitchen"
    # still not logged in afterwards
    assert client.get("/api/auth/me").status_code == 401


def test_status_check_wrong_password_is_401_and_reveals_nothing(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    r = client.post("/api/auth/application-status/check", json={
        "email": "rita@gmail.com", "password": "Wrong1234!"})
    assert r.status_code == 401
    assert "Kitchen" not in r.get_data(as_text=True)


def test_status_check_shows_rejection_remarks(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    approval = AdminApproval.query.one()
    approval.status = "rejected"
    approval.remarks = "Incomplete address."
    db.session.commit()
    body = client.post("/api/auth/application-status/check", json={
        "email": "rita@gmail.com", "password": STRONG_PASSWORD}).get_json()
    assert body["status"] == "rejected"
    assert body["remarks"] == "Incomplete address."


def test_status_check_for_customer_is_404(client):
    make_user("a@example.com")
    r = client.post("/api/auth/application-status/check", json={
        "email": "a@example.com", "password": STRONG_PASSWORD})
    assert r.status_code == 404


def test_status_check_is_throttled(client):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    for _ in range(5):
        client.post("/api/auth/application-status/check", json={
            "email": "rita@gmail.com", "password": "Wrong1234!"})
    r = client.post("/api/auth/application-status/check", json={
        "email": "rita@gmail.com", "password": STRONG_PASSWORD})
    assert r.status_code == 429


def test_status_check_does_not_leak_other_applicants(client, app):
    client.post("/api/auth/restaurant-admin/apply", json=APPLY)
    other = dict(APPLY, email="sam@gmail.com", restaurant_name="Sam's Grill")
    client.post("/api/auth/restaurant-admin/apply", json=other)
    body = client.post("/api/auth/application-status/check", json={
        "email": "rita@gmail.com", "password": STRONG_PASSWORD}).get_json()
    assert body["restaurant_name"] == "Rita's Kitchen"
