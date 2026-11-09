"""
Initialize and migrate the runtime MySQL 'fooddna' database, and seed initial demo accounts/dishes.
"""

import os
import re
import sys
from pathlib import Path

# Load dotenv if present
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

import pymysql
from werkzeug.security import generate_password_hash

DB_NAME = os.getenv("DB_NAME", "fooddna")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

STRONG_PASSWORD = "Password123!"


def _split_sql(text):
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


def main():
    print(f"Connecting to MySQL on {DB_HOST}:{DB_PORT} as {DB_USER}...")
    admin = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
    )
    with admin.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
    admin.close()

    print(f"Applying schema and migrations to `{DB_NAME}`...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
    )

    sql_files = [project_root / "database" / "schema.sql"]
    sql_files += sorted((project_root / "database" / "migrations").glob("*.sql"))

    with conn.cursor() as cur:
        for sql_file in sql_files:
            print(f"  Executing {sql_file.name}...")
            content = sql_file.read_text(encoding="utf-8")
            for statement in _split_sql(content):
                if re.match(r"(?i)^(CREATE DATABASE|USE)\b", statement):
                    continue
                try:
                    cur.execute(statement)
                except pymysql.MySQLError as err:
                    code = getattr(err, "args", [None])[0]
                    # 1060: duplicate column, 1061: duplicate key, 1826: duplicate foreign key
                    if code in {1060, 1061, 1826}:
                        continue
                    print(
                        f"    Warning on statement '{statement[:50]}...': {err}"
                    )

    # Now use Flask app context to seed initial roles, test accounts, categories, and dishes
    sys.path.insert(0, str(project_root / "backend"))
    from app import create_app
    from app.extensions import db
    from app.models import (
        DeliveryPartner,
        FoodCategory,
        Meal,
        Restaurant,
        RestaurantAdmin,
        Role,
        Staff,
        User,
    )

    app = create_app()
    with app.app_context():
        # 1. Seed Roles
        roles_map = {}
        for r_name in [
            "customer",
            "restaurant_admin",
            "staff",
            "delivery_partner",
            "super_admin",
        ]:
            role = Role.query.filter_by(name=r_name).first()
            if not role:
                role = Role(name=r_name)
                db.session.add(role)
                db.session.flush()
            roles_map[r_name] = role

        db.session.commit()
        print("  Roles verified.")

        # 2. Seed Demo Restaurant
        restaurant = Restaurant.query.filter_by(
            name="Spice Symphony Kitchen"
        ).first()
        if not restaurant:
            restaurant = Restaurant(
                name="Spice Symphony Kitchen",
                address="108 Indiranagar 100ft Road, Bangalore",
                email="contact@spicesymphony.com",
                phone="+91 9876543210",
                status="approved",
            )
            db.session.add(restaurant)
            db.session.flush()
            print("  Created demo restaurant: Spice Symphony Kitchen")

        # 3. Seed Demo Users
        password_hash = generate_password_hash(STRONG_PASSWORD)

        # Super Admin
        admin_user = User.query.filter_by(email="admin@gmail.com").first()
        if not admin_user:
            admin_user = User(
                full_name="Super Administrator",
                email="admin@gmail.com",
                password_hash=password_hash,
                role_id=roles_map["super_admin"].id,
                account_status="active",
                approval_status="not_required",
                is_active=True,
            )
            db.session.add(admin_user)
            db.session.flush()
            print("  Created demo Super Admin: admin@gmail.com")

        # Restaurant Admin
        rest_admin = User.query.filter_by(email="restaurant@gmail.com").first()
        if not rest_admin:
            rest_admin = User(
                full_name="Chef Vikram Sharma",
                email="restaurant@gmail.com",
                password_hash=password_hash,
                role_id=roles_map["restaurant_admin"].id,
                account_status="active",
                approval_status="approved",
                is_active=True,
            )
            db.session.add(rest_admin)
            db.session.flush()
            db.session.add(
                RestaurantAdmin(
                    user_id=rest_admin.id, restaurant_id=restaurant.id
                )
            )
            print("  Created demo Restaurant Admin: restaurant@gmail.com")

        # Kitchen Staff
        staff_user = User.query.filter_by(email="staff@gmail.com").first()
        if not staff_user:
            staff_user = User(
                full_name="Staff Rahul Kumar",
                email="staff@gmail.com",
                password_hash=password_hash,
                role_id=roles_map["staff"].id,
                account_status="active",
                approval_status="not_required",
                is_active=True,
            )
            db.session.add(staff_user)
            db.session.flush()
            db.session.add(
                Staff(
                    user_id=staff_user.id,
                    restaurant_id=restaurant.id,
                    designation="Head Chef",
                )
            )
            print("  Created demo Kitchen Staff: staff@gmail.com")

        # Delivery Partner
        delivery_user = User.query.filter_by(email="delivery@gmail.com").first()
        if not delivery_user:
            delivery_user = User(
                full_name="Rider Amit Verma",
                email="delivery@gmail.com",
                password_hash=password_hash,
                role_id=roles_map["delivery_partner"].id,
                account_status="active",
                approval_status="not_required",
                is_active=True,
            )
            db.session.add(delivery_user)
            db.session.flush()
            db.session.add(
                DeliveryPartner(
                    user_id=delivery_user.id,
                    phone="+91 9988776655",
                    availability_status="available",
                )
            )
            print("  Created demo Delivery Partner: delivery@gmail.com")

        # Customer
        customer_user = User.query.filter_by(email="customer@gmail.com").first()
        if not customer_user:
            customer_user = User(
                full_name="Priya Patel",
                email="customer@gmail.com",
                password_hash=password_hash,
                role_id=roles_map["customer"].id,
                account_status="active",
                approval_status="not_required",
                is_active=True,
            )
            db.session.add(customer_user)
            db.session.flush()
            print("  Created demo Customer: customer@gmail.com")

        # 4. Seed Categories
        categories_data = [
            ("North Indian", "Authentic gravies, flatbreads, and aromatic rice"),
            ("Tandoor & Grills", "Charcoal roasted skewers and smoky platters"),
            ("Healthy Bowls", "Nutrient-packed grain and protein power bowls"),
            ("South Indian", "Crispy dosas, fluffy idlis, and coconut chutneys"),
            ("Desserts & Drinks", "Artisanal sweets and cooling beverages"),
        ]
        cat_map = {}
        for cat_name, desc in categories_data:
            cat = FoodCategory.query.filter_by(name=cat_name).first()
            if not cat:
                cat = FoodCategory(name=cat_name, description=desc)
                db.session.add(cat)
                db.session.flush()
            cat_map[cat_name] = cat

        # 5. Seed Dishes
        meals_data = [
            {
                "name": "Royal Paneer Tikka Bowl",
                "category": "Healthy Bowls",
                "price": "340.00",
                "cuisine": "Indian",
                "meal_type": "Main Course",
                "taste": "Savory",
                "spice_level": "Medium",
                "portion_size": "Regular",
                "food_type": "Veg",
                "dietary": "High-Protein, Vegetarian",
                "image": "img/paneer_tikka.jpg",
                "desc": "Char-grilled cottage cheese cubes layered over aromatic saffron quinoa, roasted bell peppers, fresh microgreens, and minted greek yogurt.",
            },
            {
                "name": "Nourish Superfood Harvest Bowl",
                "category": "Healthy Bowls",
                "price": "310.00",
                "cuisine": "Continental",
                "meal_type": "Lunch",
                "taste": "Tangy",
                "spice_level": "Mild",
                "portion_size": "Regular",
                "food_type": "Vegan",
                "dietary": "Vegan, Gluten-Free",
                "image": "img/hero_bowl.jpg",
                "desc": "Edamame, avocado wedges, roasted sweet potato, baby spinach, toasted pumpkin seeds, and citrus-tahini dressing.",
            },
            {
                "name": "Smoky Dal Makhani with Garlic Naan",
                "category": "North Indian",
                "price": "280.00",
                "cuisine": "Indian",
                "meal_type": "Dinner",
                "taste": "Rich",
                "spice_level": "Medium",
                "portion_size": "Large",
                "food_type": "Veg",
                "dietary": "Vegetarian",
                "image": "",
                "desc": "Slow-cooked black lentils simmered overnight with churned butter and Kashmiri spices, served with clay oven garlic naan.",
            },
            {
                "name": "Claypot Chicken Biryani",
                "category": "North Indian",
                "price": "390.00",
                "cuisine": "Indian",
                "meal_type": "Main Course",
                "taste": "Spicy",
                "spice_level": "Hot",
                "portion_size": "Large",
                "food_type": "Non-Veg",
                "dietary": "Halal",
                "image": "",
                "desc": "Fragrant long-grain basmati layered with tender spiced chicken cuts, fried shallots, saffron milk, and cooling burani raita.",
            },
        ]

        for m in meals_data:
            existing = Meal.query.filter_by(
                name=m["name"], restaurant_id=restaurant.id
            ).first()
            if not existing:
                meal = Meal(
                    restaurant_id=restaurant.id,
                    category_id=cat_map[m["category"]].id,
                    name=m["name"],
                    description=m["desc"],
                    price=m["price"],
                    cuisine=m["cuisine"],
                    meal_type=m["meal_type"],
                    taste=m["taste"],
                    spice_level=m["spice_level"],
                    portion_size=m["portion_size"],
                    food_type=m["food_type"],
                    dietary_preference=m["dietary"],
                    image_url=m["image"] or None,
                    is_available=True,
                )
                db.session.add(meal)

        db.session.commit()
        print("  Database initialization & demo data seeding completed!")

    conn.close()


if __name__ == "__main__":
    main()
