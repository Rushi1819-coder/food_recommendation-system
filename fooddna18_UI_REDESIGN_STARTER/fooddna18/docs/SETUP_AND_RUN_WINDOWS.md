# Food DNA - Complete Windows Setup & Execution Guide

This guide provides step-by-step instructions for setting up, running, testing, and verifying the **Food DNA** application on Windows with PowerShell.

---

## 1. Prerequisites

Before starting, ensure you have the following installed on Windows:
1. **Python 3.10+** (verified and fully tested with Python 3.14.6)
2. **MySQL Server 8.0** running on default port `3306`
3. **PowerShell** (Windows default) or Windows Terminal

---

## 2. Setting Up MySQL Databases

Food DNA uses two MySQL databases:
- `fooddna` (Application runtime database)
- `fooddna_test` (Automated pytest database, wiped and recreated per test run)

Open PowerShell and log into MySQL to create both databases:

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fooddna CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fooddna_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## 3. Environment Configuration (`.env`)

In the project root directory (`fooddna18/`), create or verify your `.env` file. A sample `.env.example` is provided:

```ini
# Flask Environment
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secure-random-secret-key-min-32-chars
CSRF_SECRET_KEY=your-secure-csrf-secret-key-min-32-chars

# Database Connections (Format: mysql+pymysql://<user>:<password>@localhost:3306/<database>)
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/fooddna
TEST_DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/fooddna_test

# Security & CORS
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

> **Note:** Replace `YOUR_PASSWORD` with your local MySQL root password. Never commit `.env` to version control.

---

## 4. Python Virtual Environment Setup

From the project root (`fooddna18/`):

```powershell
# 1. Create a Python virtual environment (if not already created)
python -m venv venv

# 2. Allow PowerShell script execution for the current session (if blocked)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Running the Complete Automated Test Suite

Food DNA includes a comprehensive test suite covering authentication, RBAC, input sanitization, meal ordering, Food Memory, reverse searching, staff queues, and delivery fulfillment.

Run the test suite against `fooddna_test`:

```powershell
.\venv\Scripts\pytest.exe -q
```

Expected result:
```text
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
.............................................                            [100%]
333 passed in ~30-330s
```

All 333 tests pass with 0 failures and 0 errors.

---

## 6. Running the Application (Local Development)

To run the application, open **two separate PowerShell windows**:

### Terminal 1: Start the Backend (Flask API Server on Port 5000)

```powershell
cd c:\Users\Hello\Desktop\fooddna\fooddna18_UI_REDESIGN_STARTER\fooddna18
.\venv\Scripts\Activate.ps1
python run.py
```

- Flask API server will start at: `http://127.0.0.1:5000`
- API Health Check endpoint: `http://127.0.0.1:5000/api/health`

### Terminal 2: Start the Frontend (Static Web Server on Port 5500)

```powershell
cd c:\Users\Hello\Desktop\fooddna\fooddna18_UI_REDESIGN_STARTER\fooddna18\frontend
python -m http.server 5500
```

- Web Application will be live at: `http://127.0.0.1:5500`

---

## 7. Platform Role Demonstration Accounts

You can log in at `http://127.0.0.1:5500/login.html` using the interactive Role Selector:

| Role | Email | Password | Primary Portal Screen |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer@gmail.com` | `Password123!` | `dashboard.html` |
| **Restaurant Admin** | `restaurant@gmail.com` | `Password123!` | `restaurant-management.html` |
| **Kitchen Staff** | `staff@gmail.com` | `Password123!` | `staff-dashboard.html` |
| **Delivery Partner** | `delivery@gmail.com` | `Password123!` | `delivery-dashboard.html` |
| **Super Admin** | `admin@gmail.com` | `Password123!` | `admin-dashboard.html` |

*(If you seeded custom accounts or registered fresh ones, use the credentials you created.)*

---

## 8. Complete 21-Screen Architectural Verification

The frontend has been completely redesigned to match the 21-screen visual design collage (`FoodDNA_UI_Reference_Collage.png`) with zero placeholder text:

1. **Screen 1 (`login.html`)**: Split luxury hero with quick Role Selector pills (Customer, Restaurant, Staff, Delivery, Admin) and password toggle.
2. **Screen 2 (`register.html`)**: Live Unicode name verification and `@gmail.com` email constraint validation.
3. **Screen 3 (`dashboard.html`)**: Customer Dashboard with dynamic "Your Food DNA" taste fingerprint, live order ticker, and recommendations.
4. **Screen 4 (`menu.html`)**: Food catalog with category scroll pills (Veg, Non-Veg, Vegan, Indian, Italian, Chinese) and dropdown filters.
5. **Screen 5 (`meal.html`)**: Dish detail view with spice meter, taste profile chips, and quantity increment controls.
6. **Screen 6 (`cart.html`)**: Dual-zone cart layout with restaurant details, dish quantities, and fee breakdown.
7. **Screen 7 (`checkout.html`)**: Step 1 - Saved delivery addresses selector and add new address inline form.
8. **Screen 8 (`checkout.html`)**: Step 2 & 3 - Payment options with Cash on Delivery preselected as authoritative payment method.
9. **Screen 9 (`order-details.html`)**: Live order tracking timeline with real-time progress steps (`placed` -> `preparing` -> `out_for_delivery` -> `delivered`).
10. **Screen 10 (`orders.html`)**: My Orders list with Active and Past orders tabs, track order, and reorder affordances.
11. **Screen 11 (`food-memory.html`)**: Food Memory system featuring Favourite Meals and personal ordering activity timeline.
12. **Screen 12 (`feedback.html`)**: Ratings & Reviews with average score meter, 5-star submission form, and community review feed.
13. **Screen 13 (`reverse-ordering.html`)**: Natural-language craving search with keyword tags (e.g. "creamy paneer", "spicy garlic noodles").
14. **Screen 14 (`preferences.html`)**: Interactive Food DNA preferences choice chips (Cuisine, Spice Level, Dietary restrictions, Portion, Budget).
15. **Screen 15 (`profile.html`)**: Customer Profile with personal details, saved address management CRUD, and password update.
16. **Screen 16 (`restaurant-management.html`)**: Restaurant Admin Dashboard with KPI counters, live order status controls, and kitchen stats.
17. **Screen 17 (`restaurant-management.html`)**: Menu Catalog management with dish creation form, price controls, and availability toggles.
18. **Screen 18 (`staff-dashboard.html`)**: Kitchen Staff live order queue with status transitions (`confirmed` -> `preparing` -> `ready_for_pickup`).
19. **Screen 19 (`delivery-dashboard.html`)**: Delivery Partner portal to claim ready kitchen orders and complete Cash on Delivery dropoffs.
20. **Screen 20 (`admin-dashboard.html`)**: Super Admin overview with platform KPIs and restaurant partner approval/rejection actions.
21. **Screen 21 (`admin-users.html`)**: Super Admin user management with role filtering, account suspension toggles, and staff/rider provisioning.

---

## 9. Troubleshooting & Common Questions

### `Execution of scripts is disabled on this system`
Run PowerShell as Administrator or execute in your current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### `Can't connect to MySQL server on 'localhost:3306'`
Ensure MySQL 8.0 service is running:
```powershell
Get-Service -Name *mysql*
Start-Service -Name MySQL80   # or the specific service name on your machine
```

### `Passwords do not match or registration rejected`
- **Name**: Only letters and spaces (Unicode allowed). Digits and punctuation are automatically prevented.
- **Email**: Must end strictly with `@gmail.com`.
- **Password**: Minimum 8 characters, containing at least one uppercase letter, one lowercase letter, one number, and one special character (no spaces).
