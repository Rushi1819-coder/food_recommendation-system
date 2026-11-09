"""Phase 2: application startup, database connection, schema agreement."""

from sqlalchemy import inspect

from app.extensions import db
from app.models import Role

EXPECTED_ROLES = {
    "customer", "restaurant_admin", "staff", "delivery_partner", "super_admin",
}


def test_app_starts_and_home_works(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"


def test_database_connection(client):
    r = client.get("/api/health/db")
    assert r.status_code == 200
    assert r.get_json()["status"] == "database_ok"


def test_all_five_roles_are_seeded(app):
    names = {r.name for r in Role.query.all()}
    assert names == EXPECTED_ROLES


def test_models_match_sql_schema(app):
    """Every SQLAlchemy model column must exist in the MySQL schema
    that database/schema.sql + migrations actually create."""
    inspector = inspect(db.engine)
    db_tables = set(inspector.get_table_names())

    problems = []
    for table in db.metadata.sorted_tables:
        if table.name not in db_tables:
            problems.append(f"table missing in MySQL: {table.name}")
            continue
        db_columns = {c["name"] for c in inspector.get_columns(table.name)}
        model_columns = {c.name for c in table.columns}
        for missing in sorted(model_columns - db_columns):
            problems.append(f"{table.name}.{missing} is in the model but not MySQL")
        for extra in sorted(db_columns - model_columns):
            problems.append(f"{table.name}.{extra} is in MySQL but not the model")

    assert not problems, "\n".join(problems)


def test_unknown_route_returns_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.get_json()["success"] is False


def test_wrong_method_returns_json_405(client):
    r = client.get("/api/auth/login")
    assert r.status_code == 405
    assert r.get_json()["success"] is False
