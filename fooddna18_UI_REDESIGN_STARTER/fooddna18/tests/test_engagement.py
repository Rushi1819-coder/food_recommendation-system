"""Phase 10 engagement checks. Run with the full MySQL test suite in Phase 11."""
from datetime import date, timedelta

from app.extensions import db
from app.models import Notification, Offer, Restaurant
from tests.conftest import csrf_headers, login, make_user
from tests.test_browsing import add_restaurant


def test_public_offers_only_returns_current_offers_for_approved_restaurants(client, app):
    approved = add_restaurant("Offer Restaurant", status="approved")
    pending = add_restaurant("Pending Offer Restaurant", status="pending")
    today = date.today()
    db.session.add(Offer(restaurant_id=approved.id, title="Lunch offer", discount_percent="10.00",
                         start_date=today-timedelta(days=1), end_date=today+timedelta(days=2), is_active=True))
    db.session.add(Offer(restaurant_id=pending.id, title="Hidden offer", discount_percent="20.00",
                         start_date=today-timedelta(days=1), end_date=today+timedelta(days=2), is_active=True))
    db.session.commit()
    res = client.get("/api/offers")
    assert res.status_code == 200
    offers = res.get_json()["offers"]
    assert [o["title"] for o in offers] == ["Lunch offer"]


def test_notifications_are_private_to_logged_in_user(client, app):
    owner = make_user("notification-owner@example.com", role="customer")
    other = make_user("notification-other@example.com", role="customer")
    db.session.add(Notification(user_id=owner.id, title="Private", message="Owner only",
                                notification_type="test", is_read=False))
    db.session.commit()
    assert login(client, "notification-other@example.com", role="customer").status_code == 200
    res = client.get("/api/notifications")
    assert res.status_code == 200
    assert res.get_json()["notifications"] == []


def test_anonymous_user_cannot_read_notifications(client):
    res = client.get("/api/notifications")
    assert res.status_code == 401
