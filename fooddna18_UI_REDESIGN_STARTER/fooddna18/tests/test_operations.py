"""Phase 7-9 operational API checks. Written for the Phase 11 test run."""
from datetime import datetime

from app.extensions import db
from app.models import AdminApproval, Notification, Restaurant, RestaurantAdmin, User
from tests.conftest import csrf_headers, login, make_user


def test_customer_dashboard_returns_user_scoped_summary(client):
    make_user("dashboard-customer@example.com", role="customer")
    assert login(client, "dashboard-customer@example.com", role="customer").status_code == 200
    res = client.get("/api/dashboard/customer")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["summary"]["orders_total"] == 0
    assert body["summary"]["recent_orders"] == []


def test_customer_dashboard_rejects_anonymous_request(client):
    res = client.get("/api/dashboard/customer")
    assert res.status_code == 401


def test_super_admin_can_approve_restaurant_application(client):
    applicant = make_user("pending-admin@example.com", role="restaurant_admin",
                          account_status="pending", approval_status="pending")
    restaurant = Restaurant(name="Review Me", address="10 Market Road", status="pending")
    db.session.add(restaurant); db.session.flush()
    db.session.add(RestaurantAdmin(user_id=applicant.id, restaurant_id=restaurant.id))
    approval = AdminApproval(user_id=applicant.id, restaurant_id=restaurant.id,
                             approval_type="restaurant_admin", status="pending")
    db.session.add(approval); db.session.commit()

    make_user("root-operator@example.com", role="super_admin")
    assert login(client, "root-operator@example.com", role="super_admin").status_code == 200
    res = client.patch(f"/api/admin/approvals/{approval.id}",
                       json={"status": "approved", "remarks": "Documents reviewed"},
                       headers=csrf_headers(client))
    assert res.status_code == 200
    db.session.refresh(applicant); db.session.refresh(restaurant); db.session.refresh(approval)
    assert applicant.approval_status == "approved"
    assert applicant.account_status == "active"
    assert restaurant.status == "approved"
    assert approval.reviewed_by is not None
    assert Notification.query.filter_by(user_id=applicant.id, notification_type="approval").count() == 1


def test_non_admin_cannot_review_approvals(client):
    make_user("regular-customer@example.com", role="customer")
    assert login(client, "regular-customer@example.com", role="customer").status_code == 200
    res = client.get("/api/admin/approvals")
    assert res.status_code == 403


def test_super_admin_operator_creation_enforces_new_account_validation(client):
    """New staff/delivery accounts must use letters/spaces, Gmail and a strong password."""
    make_user("operator-admin@example.com", role="super_admin")
    assert login(client, "operator-admin@example.com", role="super_admin").status_code == 200
    headers = csrf_headers(client)
    base = {
        "full_name": "Ravi Kumar",
        "email": "ravi.delivery@gmail.com",
        "password": "StrongPass123!",
        "role": "delivery_partner",
    }
    good = client.post("/api/admin/users", json=base, headers=headers)
    assert good.status_code == 201, good.get_json()

    bad_domain = client.post("/api/admin/users", json={**base, "email": "ravi@yahoo.com"}, headers=headers)
    assert bad_domain.status_code == 400
    bad_name = client.post("/api/admin/users", json={**base, "email": "other.delivery@gmail.com", "full_name": "Ravi-123"}, headers=headers)
    assert bad_name.status_code == 400
    weak_password = client.post("/api/admin/users", json={**base, "email": "weak.delivery@gmail.com", "password": "abcdefghij"}, headers=headers)
    assert weak_password.status_code == 400
