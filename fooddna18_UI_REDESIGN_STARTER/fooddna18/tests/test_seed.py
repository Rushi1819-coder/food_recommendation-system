"""Phase 4: the development-only seed script and dev-database initialiser.

These tests run the seed against the TEST database (fooddna_test) only.
They never touch the real "fooddna" database or fooddna_dev.
"""

import ast
from pathlib import Path

import pytest

import init_dev_database
import seed_demo_data
from app.extensions import db
from app.models import FoodCategory, Meal, Restaurant, User
from tests.conftest import make_user

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def counts():
    return {
        "categories": FoodCategory.query.count(),
        "restaurants": Restaurant.query.count(),
        "meals": Meal.query.count(),
    }


# ----- the data itself -----------------------------------------------------

def test_demo_data_is_internally_consistent():
    restaurant_names = {row[0] for row in seed_demo_data.RESTAURANTS}
    category_names = {row[0] for row in seed_demo_data.CATEGORIES}
    assert len(seed_demo_data.MEALS) == 35
    for meal in seed_demo_data.MEALS:
        assert len(meal) == 13
        assert meal[0] in restaurant_names
        assert meal[1] in category_names
    pairs = [(m[0], m[2]) for m in seed_demo_data.MEALS]
    assert len(pairs) == len(set(pairs)), "duplicate (restaurant, meal) rows"


def test_demo_data_is_clearly_fictional():
    for name, _description, address, _status in seed_demo_data.RESTAURANTS:
        assert name.startswith("Demo ")
        assert address.startswith("Demo address")


# ----- seeding behaviour ---------------------------------------------------

def test_seed_creates_expected_rows(app):
    created = seed_demo_data.seed(db.session)
    db.session.commit()
    assert created == {"categories": 9, "restaurants": 7, "meals": 35}
    assert counts() == created


def test_seed_is_safe_to_run_repeatedly(app):
    seed_demo_data.seed(db.session)
    db.session.commit()
    before = counts()

    again = seed_demo_data.seed(db.session)
    db.session.commit()
    assert again == {"categories": 0, "restaurants": 0, "meals": 0}
    assert counts() == before


def test_seed_never_overwrites_existing_rows(app):
    seed_demo_data.seed(db.session)
    db.session.commit()

    meal = Meal.query.filter_by(name="Paneer Tikka").first()
    meal.price = 999
    restaurant = Restaurant.query.filter_by(name="Demo Spice Garden").first()
    restaurant.description = "Edited by a developer"
    db.session.commit()

    seed_demo_data.seed(db.session)
    db.session.commit()

    assert float(Meal.query.filter_by(name="Paneer Tikka").first().price) == 999
    assert (
        Restaurant.query.filter_by(name="Demo Spice Garden").first().description
        == "Edited by a developer"
    )


def test_seed_does_not_touch_users_or_existing_real_rows(app):
    user = make_user("keep@example.com")
    real = Restaurant(name="My Real Cafe", address="Somewhere", status="approved")
    db.session.add(real)
    db.session.commit()

    seed_demo_data.seed(db.session)
    db.session.commit()

    assert User.query.filter_by(email="keep@example.com").count() == 1
    assert db.session.get(User, user.id).email == "keep@example.com"
    assert Restaurant.query.filter_by(name="My Real Cafe").count() == 1


def test_seed_only_flushes_so_nothing_persists_until_commit(app):
    """seed() never commits; run() commits once, or rolls back on error."""
    seed_demo_data.seed(db.session)
    db.session.rollback()
    assert counts() == {"categories": 0, "restaurants": 0, "meals": 0}


def test_seeded_data_behaves_correctly_through_the_public_api(client):
    from app.extensions import db as _db

    seed_demo_data.seed(_db.session)
    _db.session.commit()

    restaurants = client.get("/api/restaurants?page_size=50").get_json()
    names = [r["name"] for r in restaurants["restaurants"]]
    assert len(names) == 6
    assert "Demo Pending Kitchen (not approved)" not in names

    meals = client.get("/api/meals?page_size=50").get_json()["meals"]
    meal_names = {m["name"] for m in meals}
    assert "Seasonal Special Curry" not in meal_names    # unavailable
    assert "Retired Mango Sundae" not in meal_names      # inactive category
    assert "Hidden Pending Thali" not in meal_names      # unapproved restaurant
    assert len(meals) == 32

    categories = [
        c["name"] for c in client.get("/api/categories").get_json()["categories"]
    ]
    assert "Retired Specials (demo, inactive)" not in categories


# ----- safety guards ---------------------------------------------------------

@pytest.mark.parametrize(
    "environment, database",
    [
        ("production", "fooddna_dev"),
        ("", "fooddna_dev"),
        (None, "fooddna_dev"),
        ("development", "fooddna"),
        ("development", "FOODDNA"),
        ("development", "fooddna_test"),
        ("development", "somethingelse"),
        ("development", ""),
        ("development", None),
    ],
)
def test_validate_target_refuses_unsafe_targets(environment, database):
    with pytest.raises(seed_demo_data.SeedRefused):
        seed_demo_data.validate_target(environment, database)


@pytest.mark.parametrize("database", ["fooddna_dev", "my_other_dev"])
def test_validate_target_accepts_dev_databases(database):
    seed_demo_data.validate_target("development", database)


def test_run_refuses_the_real_database_before_connecting():
    class RealDatabaseConfig:
        ENVIRONMENT = "development"
        SQLALCHEMY_DATABASE_URI = "mysql+pymysql://u:p@localhost:3306/fooddna"

    with pytest.raises(seed_demo_data.SeedRefused):
        seed_demo_data.run(RealDatabaseConfig)


def test_run_refuses_production_environment():
    class ProductionConfig:
        ENVIRONMENT = "production"
        SQLALCHEMY_DATABASE_URI = "mysql+pymysql://u:p@localhost:3306/fooddna_dev"

    with pytest.raises(seed_demo_data.SeedRefused):
        seed_demo_data.run(ProductionConfig)


def _destructive_calls(path):
    """Return a list of risky operations found by parsing the source."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    risky_methods = {"delete", "drop", "drop_all", "truncate", "execute"}
    risky_words = ("drop ", "truncate", "delete from", "alter table")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in risky_methods:
                found.append(f"call to .{node.func.attr}()")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            # Ignore the module docstring and long prose strings.
            if len(node.value) < 80 and any(w in lowered for w in risky_words):
                found.append(f"string {node.value!r}")
    return found


def test_seed_has_no_destructive_operations():
    assert _destructive_calls(BACKEND / "seed_demo_data.py") == []


def test_seed_is_not_imported_by_the_application():
    app_dir = BACKEND / "app"
    for source in app_dir.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "seed_demo_data" not in text, source


# ----- dev-database initialiser ------------------------------------------------

@pytest.mark.parametrize("name", ["fooddna", "FOODDNA", "", "x;drop", "my db_dev", "prod", "fooddna_dev; --"])
def test_init_dev_database_refuses_bad_names(name):
    with pytest.raises(ValueError):
        init_dev_database.check_database_name(name)


@pytest.mark.parametrize("name", ["fooddna_dev", "my_other_dev", "Test1_dev"])
def test_init_dev_database_accepts_dev_names(name):
    init_dev_database.check_database_name(name)


def test_init_dev_database_default_is_fooddna_dev():
    assert init_dev_database.DEFAULT_NAME == "fooddna_dev"


def test_init_dev_database_never_drops_or_truncates():
    tree = ast.parse((BACKEND / "init_dev_database.py").read_text(encoding="utf-8"))
    text = ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if len(node.value) < 120:
                text += node.value.lower() + "\n"
    for word in ("drop database", "drop table", "truncate", "delete from"):
        assert word not in text


def test_split_sql_removes_comments_and_blank_statements():
    sql = "-- comment\nUSE x;\n/* block */\nCREATE TABLE t (id INT);\n;\n"
    assert init_dev_database.split_sql(sql) == ["USE x", "CREATE TABLE t (id INT)"]


def test_sql_files_include_schema_and_migrations():
    files = [p.name for p in init_dev_database.sql_files()]
    assert files[0] == "schema.sql"
    assert "001_initial_schema.sql" in files
    assert "002_auth_support.sql" in files
