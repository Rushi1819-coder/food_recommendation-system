import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.models import UserAddress
from tests.conftest import STRONG_PASSWORD, login, make_user


def test_user_profile_and_update(client):
    user = make_user("profile.user@gmail.com")
    login(client, user.email)

    # Fetch profile
    res = client.get("/api/user/profile")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["profile"]["email"] == "profile.user@gmail.com"
    assert data["profile"]["full_name"] == "Test Person"

    # Get CSRF
    csrf_res = client.get("/api/auth/csrf")
    csrf_token = csrf_res.get_json()["csrf_token"]

    # Update name with valid Unicode letters
    patch_res = client.patch(
        "/api/user/profile",
        json={"full_name": "Rushi Sharma"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["user"]["full_name"] == "Rushi Sharma"

    # Update name with invalid characters rejected
    bad_res = client.patch(
        "/api/user/profile",
        json={"full_name": "Rushi123"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert bad_res.status_code == 400


def test_user_addresses_lifecycle(client):
    user = make_user("address.test@gmail.com")
    login(client, user.email)

    csrf_token = client.get("/api/auth/csrf").get_json()["csrf_token"]

    # Add first address (should automatically become default)
    add1 = client.post(
        "/api/user/addresses",
        json={"label": "Home", "full_address": "123 Green Park, Bangalore - 560001"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert add1.status_code == 201
    addr1 = add1.get_json()["address"]
    assert addr1["is_default"] is True
    assert addr1["label"] == "Home"

    # Add second address with is_default=True
    add2 = client.post(
        "/api/user/addresses",
        json={
            "label": "Office",
            "full_address": "Tech Park, Whitefield, Bangalore",
            "is_default": True,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert add2.status_code == 201
    addr2 = add2.get_json()["address"]
    assert addr2["is_default"] is True

    # Check list - addr2 should be default, addr1 non-default
    list_res = client.get("/api/user/addresses")
    assert list_res.status_code == 200
    addresses = list_res.get_json()["addresses"]
    assert len(addresses) == 2
    assert addresses[0]["id"] == addr2["id"]
    assert addresses[0]["is_default"] is True

    # Set addr1 back to default
    def_res = client.patch(
        f"/api/user/addresses/{addr1['id']}/default",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert def_res.status_code == 200
    assert def_res.get_json()["address"]["is_default"] is True

    # Delete addr2
    del_res = client.delete(
        f"/api/user/addresses/{addr2['id']}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_res.status_code == 200

    # Remaining list has 1 address
    list_after = client.get("/api/user/addresses").get_json()["addresses"]
    assert len(list_after) == 1
    assert list_after[0]["id"] == addr1["id"]


def test_reverse_food_search(client):
    # Empty query
    empty_res = client.get("/api/meals/reverse-search")
    assert empty_res.status_code == 200
    assert empty_res.get_json()["results"] == []

    # Text query
    search_res = client.get("/api/meals/reverse-search?q=spicy+under+500")
    assert search_res.status_code == 200
    data = search_res.get_json()
    assert data["success"] is True
    assert "results" in data
