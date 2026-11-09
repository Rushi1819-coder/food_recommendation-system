"""
Test setup.

SAFETY: tests run against a SEPARATE database (default: fooddna_test),
which is DROPPED and re-created from database/schema.sql plus the
migration files at the start of every test run. The real "fooddna"
database is never touched. If the test database name is ever the same
as DB_NAME, or does not end in "_test", the tests refuse to run.
"""

import os
import re
from pathlib import Path

import pymysql
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Role, User
from app.utils import rate_limit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "fooddna_test")

STRONG_PASSWORD = "Passw0rd!"


def _split_sql(text):
    """Split an SQL file into single statements (files have no
    semicolons inside string literals)."""
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


def _connect(database=None):
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database,
        autocommit=True,
    )


@pytest.fixture(scope="session", autouse=True)
def test_database():
    real_db = os.getenv("DB_NAME", "fooddna")

    if TEST_DB_NAME == real_db or not TEST_DB_NAME.endswith("_test"):
        pytest.exit(
            f"Refusing to run: TEST_DB_NAME ('{TEST_DB_NAME}') must differ "
            f"from DB_NAME ('{real_db}') and end with '_test'.",
            returncode=2,
        )

    admin = _connect()
    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS `{TEST_DB_NAME}`")
        cur.execute(
            f"CREATE DATABASE `{TEST_DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    admin.close()

    conn = _connect(TEST_DB_NAME)
    sql_files = [PROJECT_ROOT / "database" / "schema.sql"]
    sql_files += sorted((PROJECT_ROOT / "database" / "migrations").glob("*.sql"))

    with conn.cursor() as cur:
        for sql_file in sql_files:
            for statement in _split_sql(sql_file.read_text(encoding="utf-8")):
                # The files name the real database; the test run must
                # use the test database instead.
                if re.match(r"(?i)^(CREATE DATABASE|USE)\b", statement):
                    continue
                try:
                    cur.execute(statement)
                except pymysql.MySQLError as err:
                    if getattr(err, "args", [None])[0] in {1061, 1060, 1826}:
                        continue
                    raise
    conn.close()

    yield

    # Leave the test database in place so a failure can be inspected.


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    rate_limit.reset_all()

    with application.app_context():
        _truncate_all_except_roles()
        yield application
        db.session.remove()


def _truncate_all_except_roles():
    db.session.rollback()
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0"))
    for table in db.metadata.sorted_tables:
        if table.name != "roles":
            db.session.execute(db.text(f"TRUNCATE TABLE `{table.name}`"))
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1"))
    db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


# ----- helpers used by many tests ---------------------------------

def make_user(
    email,
    role="customer",
    password=STRONG_PASSWORD,
    account_status="active",
    approval_status="not_required",
    is_active=True,
    full_name="Test Person",
):
    role_row = Role.query.filter_by(name=role).first()
    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role_id=role_row.id,
        account_status=account_status,
        approval_status=approval_status,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email, role="customer", password=STRONG_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "role": role},
    )


def csrf_headers(client):
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    return {"X-CSRF-Token": token}
