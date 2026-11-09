# 🍽️ FoodDNA — Smart Food Recommendation System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql&logoColor=white)](https://www.mysql.com)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?logo=bootstrap&logoColor=white)](https://getbootstrap.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **FoodDNA** is a full-stack food ordering and personalised meal recommendation platform that learns your taste preferences and recommends dishes with a match-percentage score. Built with Flask, MySQL, and vanilla JavaScript.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔐 **Authentication & RBAC** | Registration, login, sessions, CSRF protection, password reset, role-based access (Customer, Restaurant Admin, Staff, Delivery, Super Admin) |
| 🍜 **Smart Recommendations** | Rule-based scoring engine using cuisine, taste, spice, portion, dietary, and budget preferences with match-percentage explanations |
| 🛒 **Shopping Cart & Orders** | Single-restaurant cart, server-authoritative pricing with Decimal arithmetic, atomic checkout with Cash on Delivery |
| 🧠 **Food Memory** | Timeline of food interactions (views, orders, recommendations) for personalised experience |
| 📊 **Multi-Role Dashboards** | Customer dashboard, Restaurant Admin menu management, Staff order progression, Delivery partner workflow, Super Admin operations |
| 🎯 **Offers & Engagement** | Restaurant offers with auto-discount at checkout, customer feedback, and notification system |
| 🔍 **Advanced Search & Filters** | Full-text search, multi-filter browsing (cuisine, category, price range, dietary, spice level), sorting, and pagination |
| 📱 **Responsive UI** | Mobile-first Bootstrap 5 design with dark mode support |

---

## 🏗️ Tech Stack

```
┌─────────────────────────────────────────────┐
│              Frontend (Port 5500)            │
│  HTML5 · CSS3 · JavaScript · Bootstrap 5    │
├─────────────────────────────────────────────┤
│              Backend (Port 5000)             │
│  Python · Flask · SQLAlchemy · REST API     │
├─────────────────────────────────────────────┤
│              Database                        │
│  MySQL 8.0 · PyMySQL Driver                 │
└─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
food_recommendation-system/
├── fooddna18_UI_REDESIGN_STARTER/
│   └── fooddna18/
│       ├── backend/
│       │   ├── app/
│       │   │   ├── models.py           # SQLAlchemy models (15+ tables)
│       │   │   ├── config.py           # App configuration
│       │   │   ├── extensions.py       # Flask extensions
│       │   │   ├── middleware/          # Auth middleware
│       │   │   ├── routes/             # API route blueprints
│       │   │   │   ├── auth.py         # Authentication endpoints
│       │   │   │   ├── cart.py         # Shopping cart
│       │   │   │   ├── meals.py        # Meal browsing & search
│       │   │   │   ├── orders.py       # Order management
│       │   │   │   ├── preferences.py  # User preferences
│       │   │   │   ├── recommendations.py  # Smart recommendations
│       │   │   │   ├── restaurants.py  # Restaurant browsing
│       │   │   │   └── ...
│       │   │   ├── services/           # Business logic layer
│       │   │   │   ├── recommendation_service.py  # Scoring engine
│       │   │   │   ├── food_memory_service.py     # Food Memory
│       │   │   │   └── ...
│       │   │   └── utils/              # Validation, rate limiting
│       │   ├── run.py                  # App entry point
│       │   ├── create_super_admin.py   # One-time admin setup
│       │   ├── seed_demo_data.py       # Demo data seeder
│       │   └── migrate.py             # Database migrations
│       ├── frontend/
│       │   ├── index.html              # Landing page
│       │   ├── css/style.css           # Global styles
│       │   ├── js/
│       │   │   ├── api.js              # API client & auth helpers
│       │   │   ├── layout.js           # Shared layout & navbar
│       │   │   ├── recommendations.js  # Recommendation UI
│       │   │   └── ...
│       │   ├── img/                    # Static images
│       │   └── *.html                  # Feature pages
│       ├── tests/                      # Pytest test suite
│       │   ├── test_auth.py
│       │   ├── test_recommendations.py
│       │   ├── test_cart.py
│       │   ├── test_orders.py
│       │   └── ...
│       ├── requirements.txt
│       ├── .env.example
│       └── README.md                   # Detailed documentation
├── .gitignore
└── README.md                           # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **MySQL 8.0+** (running locally)
- **pip** (Python package manager)

### 1. Clone the repository

```bash
git clone https://github.com/Rushi1819-coder/food_recommendation-system.git
cd food_recommendation-system/fooddna18_UI_REDESIGN_STARTER/fooddna18
```

### 2. Set up the virtual environment

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux/macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set:
```env
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
DB_PASSWORD=<your-mysql-root-password>
DB_NAME=fooddna
```

### 5. Set up the database

```sql
-- In MySQL client:
CREATE DATABASE IF NOT EXISTS fooddna CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Create the Super Admin account

```bash
cd backend
python create_super_admin.py
cd ..
```

### 7. Run the application

**Terminal 1 — Backend:**
```bash
cd backend
python run.py
# → Running on http://127.0.0.1:5000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
python -m http.server 5500
# → Open http://127.0.0.1:5500/index.html
```

---

## 🧪 Running Tests

```bash
# From the project root (fooddna18/ directory)
python -m pytest -q
```

Tests use a separate `fooddna_test` database (created and destroyed automatically). Your production data is never touched.

| Test File | Coverage |
|-----------|----------|
| `test_foundation.py` | App startup, DB connection, schema |
| `test_auth.py` | Registration, login, sessions, CSRF, password reset |
| `test_validation.py` | Name/email validation rules |
| `test_browsing.py` | Restaurant & meal APIs, search, filters, pagination |
| `test_preferences.py` | Preference CRUD, validation |
| `test_recommendations.py` | Scoring engine, budget/dietary filters |
| `test_cart.py` | Cart operations, restaurant conflict |
| `test_orders.py` | Checkout, pricing, transaction rollback |
| `test_operations.py` | Admin dashboard, approval workflows |
| `test_engagement.py` | Offers, feedback, notifications |

---

## 🔌 API Overview

All endpoints return JSON: `{"success": true|false, ...}`

### Public Endpoints (No Auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/restaurants` | Browse restaurants |
| `GET` | `/api/meals` | Browse meals with filters |
| `GET` | `/api/meals/filters` | Available filter values |
| `POST` | `/api/auth/register` | Customer registration |
| `POST` | `/api/auth/login` | User login |

### Customer Endpoints (Auth Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/PUT` | `/api/preferences` | Get/save food preferences |
| `POST` | `/api/recommendations` | Get personalised recommendations |
| `GET/POST` | `/api/cart` | Cart operations |
| `POST` | `/api/orders` | Place order |
| `GET` | `/api/food-memory/timeline` | Food interaction history |

> See the full API reference in [`fooddna18_UI_REDESIGN_STARTER/fooddna18/README.md`](fooddna18_UI_REDESIGN_STARTER/fooddna18/README.md)

---

## 🎯 How Recommendations Work

```
Customer Preferences → Hard Filters → Weighted Scoring → Ranked Results
                         │                  │
                    ┌────┴────┐      ┌──────┴──────┐
                    │ Budget  │      │ Cuisine: 20 │
                    │ Veg/    │      │ Meal Type:15│
                    │  Vegan  │      │ Taste:    15│
                    │ Dietary │      │ Spice:    15│
                    └─────────┘      │ Portion:  10│
                                     │ Food Type:10│
                                     │ Dietary:  10│
                                     │ Budget:    5│
                                     └─────────────┘
```

1. **Hard filters** eliminate dishes exceeding budget, non-veg (for veg users), or mismatched dietary labels
2. **Weighted scoring** computes a 0–100% match based on how many preferences each dish satisfies
3. **Results** are ranked with explanations ("Why it matches") and match percentages

---

## 👥 User Roles

| Role | Capabilities |
|------|-------------|
| **Customer** | Browse, search, set preferences, get recommendations, cart, orders, feedback |
| **Restaurant Admin** | Manage menu items, view orders, create offers |
| **Staff** | Process and progress order statuses |
| **Delivery Partner** | Claim and deliver orders |
| **Super Admin** | Approve restaurants, manage users, system operations |

---

## 🛡️ Security Features

- 🔒 Server-side session management with secure cookies
- 🛡️ CSRF token protection on all mutating endpoints
- 🔐 Bcrypt password hashing (via Werkzeug)
- 🚫 Rate limiting on login attempts
- ✅ Input validation (Unicode names, Gmail-only registration)
- 🧹 SQL injection prevention (parameterised queries via SQLAlchemy)
- 🌐 CORS whitelisting (never `*`)

---

## 📄 License

This project is for educational purposes. Feel free to use and modify.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Rushi1819-coder">Rushi1819-coder</a>
</p>
