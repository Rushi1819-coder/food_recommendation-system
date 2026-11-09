"""
Food DNA - DEVELOPMENT-ONLY demo data.

Run it yourself, on purpose, against a separate development database:

    cd backend
    python seed_demo_data.py

Safety rules (enforced in code, see validate_target):
  * FLASK_ENV must be "development".
  * The target database name must end in "_dev" (e.g. fooddna_dev) and must
    never be "fooddna", the real database.
  * It only INSERTS rows that do not exist yet. It never updates, deletes,
    drops or truncates anything, and never touches users or orders.
  * Everything runs in one transaction that is rolled back on any error.
  * It is never called from the application at startup.

All names, addresses and dishes below are fictional demo data.
"""

import sys
from decimal import Decimal

from sqlalchemy.engine import make_url

PROTECTED_DATABASES = {"fooddna"}
REQUIRED_SUFFIX = "_dev"


class SeedRefused(RuntimeError):
    """Raised when the seed script is pointed at an unsafe target."""


def validate_target(environment, database_name):
    if (environment or "").strip().lower() != "development":
        raise SeedRefused(
            "Refusing to seed: FLASK_ENV must be 'development' "
            f"(it is '{environment}')."
        )
    if not database_name:
        raise SeedRefused("Refusing to seed: no database name configured.")
    if database_name.lower() in PROTECTED_DATABASES:
        raise SeedRefused(
            f"Refusing to seed the real database '{database_name}'. "
            "Set DB_NAME=fooddna_dev for this PowerShell window (or in .env) "
            "first."
        )
    if not database_name.endswith(REQUIRED_SUFFIX):
        raise SeedRefused(
            f"Refusing to seed '{database_name}': a development database "
            f"name must end with '{REQUIRED_SUFFIX}' (for example fooddna_dev)."
        )


# ------------------------------------------------------------------
# Demo data (fictional)
# ------------------------------------------------------------------

CATEGORIES = [
    # (name, description, is_active)
    ("Starters", "Small plates to begin a meal", True),
    ("Main Course", "Hearty main dishes", True),
    ("Rice and Biryani", "Rice-based dishes", True),
    ("Breads", "Freshly baked breads", True),
    ("Snacks", "Light bites any time of day", True),
    ("Breakfast", "Morning favourites", True),
    ("Desserts", "Sweet endings", True),
    ("Beverages", "Hot and cold drinks", True),
    ("Retired Specials (demo, inactive)", "Inactive demo category", False),
]

RESTAURANTS = [
    # (name, description, address, status)
    (
        "Demo Spice Garden",
        "Fictional demo restaurant serving North Indian classics.",
        "Demo address: 1 Sample Street, Demo City",
        "approved",
    ),
    (
        "Demo South Kitchen",
        "Fictional demo restaurant with South Indian tiffin and meals.",
        "Demo address: 2 Sample Street, Demo City",
        "approved",
    ),
    (
        "Demo Dragon Wok",
        "Fictional demo restaurant for Indo-Chinese dishes.",
        "Demo address: 3 Sample Street, Demo City",
        "approved",
    ),
    (
        "Demo Pasta Corner",
        "Fictional demo restaurant with Italian comfort food.",
        "Demo address: 4 Sample Street, Demo City",
        "approved",
    ),
    (
        "Demo Taco Hub",
        "Fictional demo restaurant for Mexican street food.",
        "Demo address: 5 Sample Street, Demo City",
        "approved",
    ),
    (
        "Demo Sweet Tooth Cafe",
        "Fictional demo cafe for desserts, coffee and snacks.",
        "Demo address: 6 Sample Street, Demo City",
        "approved",
    ),
    # Not approved yet: must NOT appear on the public pages.
    (
        "Demo Pending Kitchen (not approved)",
        "Demo restaurant still waiting for approval; hidden from browsing.",
        "Demo address: 7 Sample Street, Demo City",
        "pending",
    ),
]

# One dish per line, fields separated by "|":
#   restaurant | category | name | description | price | cuisine |
#   meal_type | taste | spice_level | portion | dietary | food_type | available
# A dietary value of "-" means "not specified" (stored as NULL).
MEAL_TABLE = """
Demo Spice Garden|Starters|Paneer Tikka|Grilled cottage cheese cubes with spiced yogurt marinade.|240.00|North Indian|Dinner|Spicy|Medium|Regular|Vegetarian|Veg|yes
Demo Spice Garden|Starters|Chicken Seekh Kebab|Minced chicken skewers grilled over charcoal.|280.00|North Indian|Dinner|Spicy|Hot|Regular|High-Protein|Non-Veg|yes
Demo Spice Garden|Main Course|Dal Makhani|Slow-cooked black lentils finished with butter and cream.|220.00|North Indian|Lunch|Savory|Mild|Regular|Vegetarian|Veg|yes
Demo Spice Garden|Main Course|Butter Chicken|Tandoori chicken in a creamy tomato gravy.|320.00|North Indian|Dinner|Savory|Mild|Large|-|Non-Veg|yes
Demo Spice Garden|Main Course|Chana Masala|Chickpeas simmered in a tangy onion-tomato masala.|190.00|North Indian|Lunch|Tangy|Medium|Regular|Vegan|Vegan|yes
Demo Spice Garden|Breads|Garlic Naan|Oven-baked flatbread brushed with garlic butter.|60.00|North Indian|Dinner|Savory|None|Small|Vegetarian|Veg|yes
Demo Spice Garden|Rice and Biryani|Hyderabadi Chicken Biryani|Layered basmati rice and marinated chicken.|310.00|North Indian|Lunch|Spicy|Hot|Large|-|Non-Veg|yes
Demo Spice Garden|Main Course|Seasonal Special Curry|Temporarily out of stock demo item.|260.00|North Indian|Dinner|Savory|Medium|Regular|Vegetarian|Veg|no
Demo South Kitchen|Breakfast|Masala Dosa|Crisp rice crepe with spiced potato filling.|120.00|South Indian|Breakfast|Savory|Medium|Regular|Vegan|Vegan|yes
Demo South Kitchen|Breakfast|Idli Sambar|Steamed rice cakes served with lentil stew.|80.00|South Indian|Breakfast|Tangy|Mild|Small|Vegan|Vegan|yes
Demo South Kitchen|Breakfast|Egg Dosa|Dosa topped with a spiced egg layer.|110.00|South Indian|Breakfast|Savory|Medium|Regular|Eggetarian|Non-Veg|yes
Demo South Kitchen|Rice and Biryani|Curd Rice|Cooling yogurt rice tempered with mustard and curry leaves.|90.00|South Indian|Lunch|Mild|None|Regular|Vegetarian|Veg|yes
Demo South Kitchen|Main Course|Chettinad Chicken Curry|Pepper-forward chicken curry in a roasted spice blend.|290.00|South Indian|Dinner|Spicy|Hot|Regular|High-Protein|Non-Veg|yes
Demo South Kitchen|Beverages|Filter Coffee|Strong South Indian style coffee with milk.|50.00|South Indian|Beverage|Sweet|None|Small|Vegetarian|Veg|yes
Demo Dragon Wok|Starters|Veg Manchurian|Crisp vegetable dumplings in a tangy soy-garlic sauce.|170.00|Chinese|Dinner|Tangy|Medium|Regular|Vegetarian|Veg|yes
Demo Dragon Wok|Starters|Chilli Chicken|Wok-tossed chicken with peppers and green chillies.|260.00|Chinese|Dinner|Spicy|Hot|Regular|-|Non-Veg|yes
Demo Dragon Wok|Main Course|Hakka Noodles|Stir-fried noodles with vegetables.|160.00|Chinese|Lunch|Savory|Mild|Large|Vegan|Vegan|yes
Demo Dragon Wok|Rice and Biryani|Egg Fried Rice|Fried rice with scrambled egg and spring onion.|170.00|Chinese|Lunch|Savory|Mild|Regular|Eggetarian|Non-Veg|yes
Demo Dragon Wok|Snacks|Veg Spring Rolls|Crunchy rolls filled with cabbage and carrot.|130.00|Chinese|Snack|Savory|None|Small|Vegan|Vegan|yes
Demo Pasta Corner|Main Course|Penne Arrabbiata|Penne in a spicy tomato and garlic sauce.|250.00|Italian|Dinner|Spicy|Medium|Regular|Vegan|Vegan|yes
Demo Pasta Corner|Main Course|Margherita Pizza|Thin-crust pizza with tomato, mozzarella and basil.|300.00|Italian|Dinner|Savory|None|Large|Vegetarian|Veg|yes
Demo Pasta Corner|Main Course|Chicken Alfredo|Fettuccine in a creamy parmesan sauce with chicken.|340.00|Italian|Dinner|Savory|Mild|Large|High-Protein|Non-Veg|yes
Demo Pasta Corner|Starters|Garlic Bread|Toasted baguette with garlic butter and herbs.|110.00|Italian|Snack|Savory|None|Small|Vegetarian|Veg|yes
Demo Pasta Corner|Desserts|Tiramisu|Coffee-soaked sponge layered with mascarpone.|230.00|Italian|Dessert|Sweet|None|Small|Vegetarian|Veg|yes
Demo Taco Hub|Main Course|Bean and Corn Tacos|Three soft tacos with black beans, corn and salsa.|200.00|Mexican|Lunch|Tangy|Medium|Regular|Vegan|Vegan|yes
Demo Taco Hub|Main Course|Chicken Burrito|Flour tortilla filled with chicken, rice and beans.|280.00|Mexican|Dinner|Savory|Medium|Large|High-Protein|Non-Veg|yes
Demo Taco Hub|Snacks|Nachos with Salsa|Corn chips served with fresh tomato salsa.|150.00|Mexican|Snack|Tangy|Mild|Regular|Gluten-Free|Vegan|yes
Demo Taco Hub|Snacks|Jalapeno Quesadilla|Cheesy quesadilla with pickled jalapenos.|190.00|Mexican|Snack|Spicy|Hot|Regular|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Desserts|Gulab Jamun|Soft milk dumplings in cardamom sugar syrup.|90.00|North Indian|Dessert|Sweet|None|Small|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Desserts|Chocolate Brownie|Warm fudge brownie.|140.00|Continental|Dessert|Sweet|None|Regular|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Beverages|Cold Coffee|Chilled blended coffee with milk and ice.|120.00|Continental|Beverage|Sweet|None|Regular|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Beverages|Masala Chai|Spiced Indian tea.|40.00|North Indian|Beverage|Sweet|Mild|Small|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Snacks|Veg Club Sandwich|Toasted sandwich with vegetables and cheese.|160.00|Continental|Snack|Savory|None|Regular|Vegetarian|Veg|yes
Demo Sweet Tooth Cafe|Retired Specials (demo, inactive)|Retired Mango Sundae|Belongs to an inactive category; hidden from browsing.|150.00|Continental|Dessert|Sweet|None|Regular|Vegetarian|Veg|yes
Demo Pending Kitchen (not approved)|Main Course|Hidden Pending Thali|Must never be shown publicly.|199.00|North Indian|Lunch|Savory|Mild|Large|Vegetarian|Veg|yes
"""

MEAL_FIELDS = 13


def parse_meals():
    """Turn MEAL_TABLE into a list of 13-field tuples."""
    meals = []
    for line in MEAL_TABLE.strip().splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != MEAL_FIELDS:
            raise ValueError(f"Bad demo meal row: {line!r}")
        (restaurant, category, name, description, price, cuisine,
         meal_type, taste, spice, portion, dietary, food_type,
         available) = parts
        meals.append((
            restaurant, category, name, description, price, cuisine,
            meal_type, taste, spice, portion,
            None if dietary == "-" else dietary,
            food_type, available == "yes",
        ))
    return meals


MEALS = parse_meals()


def seed(session):
    """
    Insert missing demo rows using `session`. Does not commit.
    Existing rows are left exactly as they are. Returns a dict of counts.
    """
    from app.models import FoodCategory, Meal, Restaurant

    created = {"categories": 0, "restaurants": 0, "meals": 0}

    categories = {}
    for name, description, active in CATEGORIES:
        row = session.query(FoodCategory).filter_by(name=name).first()
        if row is None:
            row = FoodCategory(
                name=name, description=description, is_active=active
            )
            session.add(row)
            session.flush()
            created["categories"] += 1
        categories[name] = row

    restaurants = {}
    for name, description, address, status in RESTAURANTS:
        row = session.query(Restaurant).filter_by(name=name).first()
        if row is None:
            row = Restaurant(
                name=name, description=description,
                address=address, status=status,
            )
            session.add(row)
            session.flush()
            created["restaurants"] += 1
        restaurants[name] = row

    for (rest, cat, name, description, price, cuisine, meal_type, taste,
         spice, portion, dietary, food_type, available) in MEALS:
        restaurant = restaurants[rest]
        exists = (
            session.query(Meal.id)
            .filter_by(restaurant_id=restaurant.id, name=name)
            .first()
        )
        if exists:
            continue
        session.add(Meal(
            restaurant_id=restaurant.id,
            category_id=categories[cat].id,
            name=name, description=description,
            price=Decimal(price), cuisine=cuisine, meal_type=meal_type,
            taste=taste, spice_level=spice, portion_size=portion,
            dietary_preference=dietary, food_type=food_type,
            image_url=None, is_available=available,
        ))
        created["meals"] += 1

    session.flush()
    return created


def run(config_class=None):
    """Validate the target, then seed inside one transaction."""
    from app import create_app
    from app.config import Config
    from app.extensions import db

    config_class = config_class or Config
    database_name = make_url(config_class.SQLALCHEMY_DATABASE_URI).database
    validate_target(config_class.ENVIRONMENT, database_name)

    app = create_app(config_class)
    with app.app_context():
        try:
            created = seed(db.session)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return database_name, created


def main():
    try:
        database_name, created = run()
    except SeedRefused as error:
        print(f"\nSEED REFUSED: {error}\n")
        return 2
    except Exception as error:
        print(
            "\nSEED FAILED and was rolled back "
            f"({type(error).__name__}: {error}).\n"
            "Check that MySQL is running and that the development database "
            "was created with python init_dev_database.py.\n"
        )
        return 1

    print(f"Seeded database '{database_name}':")
    for key, value in created.items():
        print(f"  new {key}: {value}")
    if not any(created.values()):
        print("  (nothing to add - demo data already present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
