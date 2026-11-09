"""Name and new-account email validation rules."""

import pytest

from app.models import User
from app.utils.validation import validate_email, validate_full_name
from tests.conftest import STRONG_PASSWORD

GOOD_NAMES = [
    "Rushi Sharma",
    "José García",
    "राहुल शर्मा",
    "Mary Ann",
]

BAD_NAMES = [
    "",
    "   ",
    "Asha 123",
    "Asha123",
    "O'Brien",
    "Anne-Marie",
    "A. Kumar",
    "O’Neil",
    "Bob\x00",
    "Tab\tName",
    "<script>",
    "a" * 121,
    "...",
    "Name 😀",
    None,
    123,
    ["x"],
]

GOOD_EMAILS = [
    "a@gmail.com",
    "first.last@gmail.com",
    "first.last+tag@gmail.com",
    "RUSHI123@GMAIL.COM",
]

BAD_EMAILS = [
    "",
    "plain",
    "a@b",
    "a@b.c",
    "a@yahoo.com",
    "a@example.com",
    "a@gmail.co",
    "a@googlemail.com",
    "a@gmail.com.evil",
    "a@-gmail.com",
    "a..b@gmail.com",
    ".a@gmail.com",
    "a.@gmail.com",
    "a b@gmail.com",
    "@gmail.com",
    "a@.com",
    "a" * 250 + "@gmail.com",
    None,
    5,
    ["a@gmail.com"],
]


@pytest.mark.parametrize("name", GOOD_NAMES)
def test_good_names_accepted(name):
    assert validate_full_name(name)[0] is True


@pytest.mark.parametrize("name", BAD_NAMES)
def test_bad_names_rejected(name):
    assert validate_full_name(name)[0] is False


@pytest.mark.parametrize("email", GOOD_EMAILS)
def test_good_gmail_addresses_accepted(email):
    assert validate_email(email)[0] is True


@pytest.mark.parametrize("email", BAD_EMAILS)
def test_bad_gmail_addresses_rejected(email):
    assert validate_email(email)[0] is False


def test_register_with_gmail_and_unicode_name(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "José García",
            "email": "Jose@GMAIL.COM",
            "password": STRONG_PASSWORD,
            "confirm_password": STRONG_PASSWORD,
        },
    )
    assert response.status_code == 201, response.get_json()
    assert User.query.filter_by(email="jose@gmail.com").count() == 1


def test_register_rejects_non_gmail_and_punctuation_in_name(client):
    base = {
        "full_name": "Asha Kumar",
        "email": "asha@gmail.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }
    bad_domain = client.post("/api/auth/register", json={**base, "email": "asha@example.com"})
    assert bad_domain.status_code == 400
    bad_name = client.post("/api/auth/register", json={**base, "full_name": "Asha-Kumar"})
    assert bad_name.status_code == 400
    assert User.query.count() == 0


def test_duplicate_detection_is_case_insensitive_for_gmail(client):
    payload = {
        "full_name": "Asha Kumar",
        "email": "asha@gmail.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    payload["email"] = "ASHA@GMAIL.COM"
    assert client.post("/api/auth/register", json=payload).status_code == 409
    assert User.query.count() == 1
