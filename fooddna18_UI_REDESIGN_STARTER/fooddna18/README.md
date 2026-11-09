# Food DNA - Smart Meal Recommendation System

Full-stack food ordering and personalised food recommendation app.

- **Backend:** Python Flask, SQLAlchemy (PyMySQL), REST JSON API
- **Database:** MySQL (`fooddna`; separate `fooddna_dev` for demo data)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5

> **Status: Phases 1-10 have code in this archive.** The user reported that the full
> pytest suite passed locally before the latest account-validation policy change. Because
> this archive updates validators and test fixtures, rerun `python -m pytest -q` after
> extracting it. Browser validation of the complete workflows remains a separate step;
> do not treat a passing test suite alone as proof that every UI workflow is correct. See `docs/PROJECT_AUDIT.md`, `docs/PHASE6_PROGRESS.md`, and
> `docs/PHASE7_10_PROGRESS.md` for the exact verification status.

---

## 1. One-time setup (Windows PowerShell)

Open **PowerShell** and go to the project folder:

```powershell
cd C:\Users\Hello\Desktop\fooddna18
```

### 1.1 Create and activate the virtual environment

```powershell
python -m venv venv
# Only if PowerShell blocks the next line, allow scripts for THIS window only:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

You should now see `(venv)` at the start of the prompt.

### 1.2 Install the dependencies

```powershell
pip install -r requirements.txt
```

Phases 4 and 5 need **no new Python packages**: `requirements.txt` is unchanged
(Flask, Flask-SQLAlchemy, Flask-Cors, PyMySQL, python-dotenv, Werkzeug, pytest).

### 1.3 Create your `.env`

```powershell
copy .env.example .env
```

Open `.env` in VS Code and fill in `SECRET_KEY` and `DB_PASSWORD`.
Generate a secret key with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Never share your `.env` file or put it in a ZIP you send to anyone.**
Keep `DB_NAME=fooddna` in `.env`; the development database is selected
per PowerShell window (section 3), so `.env` never needs editing.

### 1.4 Create the real database tables

Only needed the first time (or on a new machine). If your `fooddna`
database already exists, review and apply the missing migrations (003 for cart uniqueness and 004 for operations/offer fields) only after checking the existing schema and backing up your data.

```powershell
Get-Content database\schema.sql | mysql -u root -p
Get-Content database\migrations\001_initial_schema.sql | mysql -u root -p
Get-Content database\migrations\002_auth_support.sql | mysql -u root -p
Get-Content database\migrations\003_cart_items_unique.sql | mysql -u root -p
# One-time Phase 7-10 operations update (adds order assignment/offer fields):
Get-Content database\migrations\004_operations_engagement.sql | mysql -u root -p
```

**Migration 003 Pre-Inspection (Existing Database):**
Before applying migration 003 on an existing database with data, run the inspection query:
```sql
SELECT cart_id, meal_id, COUNT(*) AS dupes, SUM(quantity) AS total_qty
FROM cart_items GROUP BY cart_id, meal_id HAVING COUNT(*) > 1;
```
If duplicates exist, do not delete blindly; follow the safe data-preserving consolidation procedure documented in `database/migrations/003_cart_items_unique.sql`.

Before migration 004 on an existing database, inspect whether its new columns already exist:
```sql
SHOW COLUMNS FROM orders LIKE 'delivery_partner_id';
SHOW COLUMNS FROM orders LIKE 'offer_id';
SHOW COLUMNS FROM orders LIKE 'discount_amount';
```
Apply migration 004 only if the columns/constraints are not already present. Back up the database first.

If `mysql` is "not recognized", use the full path, for example
`& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p`.
The base schema and table-creation statements are designed for re-runs. Migrations 003 and 004 contain `ALTER TABLE` statements: review the target schema first and do not blindly rerun them against a database where the constraints/columns may already exist.

### 1.5 Create the Super Admin (once)

```powershell
cd backend
python create_super_admin.py
cd ..
```

It refuses to create a second account with the same email.

---

## 2. Run the app (two PowerShell windows)

**Window 1 - backend:**

```powershell
cd C:\Users\Hello\Desktop\fooddna18
.\venv\Scripts\Activate.ps1
cd backend
python run.py
```

Expected: `Running on http://127.0.0.1:5000`.

**Window 2 - frontend:**

```powershell
cd C:\Users\Hello\Desktop\fooddna18\frontend
python -m http.server 5500
```

Open <http://127.0.0.1:5500/index.html> and click
**Check backend connection**. Expected: *Backend and database are connected.*

> Open the pages through `http://127.0.0.1:5500` (or `localhost:5500`).
> Double-clicking the HTML files (`file://`) will **not** work: the browser
> blocks the session cookie.

With your real `fooddna` database, the restaurant and food pages are empty until restaurants have meals. Use the Super Admin approval workflow to approve new restaurant applications, or use the separate development database below for sample catalogue content.

---

## 3. Development database and demo data (Phase 4)

Demo restaurants and dishes go into a **separate** database called
`fooddna_dev`. Your real `fooddna` database is never touched.

Safety rules (enforced in code and covered by tests that are written but not
yet run, see section 7):

- `init_dev_database.py` only accepts names ending in `_dev` and refuses
  `fooddna`. It never drops or truncates anything.
- `seed_demo_data.py` refuses to run unless `FLASK_ENV=development` **and**
  the database name ends in `_dev` (never `fooddna`).
- The seed only **inserts missing rows**. It never updates, deletes, drops or
  truncates, and never touches users or orders. Running it twice is safe: the
  second run adds nothing.
- The application never runs the seed by itself; you run it on purpose.

### 3.1 Create and fill `fooddna_dev`

Use the **backend** window (venv active, folder `backend`):

```powershell
cd C:\Users\Hello\Desktop\fooddna18
.\venv\Scripts\Activate.ps1
cd backend

# 1. Create the empty development database with all tables
python init_dev_database.py
# Expected: Database 'fooddna_dev' is ready: 24 tables (...)

# 2. Point THIS PowerShell window at the development database
$env:DB_NAME = "fooddna_dev"

# 3. Insert the demo data
python seed_demo_data.py
# First run:  new categories: 9 / new restaurants: 7 / new meals: 35
# Second run: (nothing to add - demo data already present)

# 4. Start the backend against fooddna_dev
python run.py
```

`$env:DB_NAME` only affects the window where you typed it. Your `.env` is not
changed. To go back to the real database, close that PowerShell window (or run
`Remove-Item Env:DB_NAME`) and start the backend again.

Check the data (optional):

```powershell
mysql -u root -p fooddna_dev -e "SELECT COUNT(*) FROM meals;"
```

If you run `python seed_demo_data.py` **without** `$env:DB_NAME`, it prints
`SEED REFUSED` and changes nothing.

### 3.2 What the demo data contains

7 fictional restaurants (names start with `Demo`), 9 categories and 35 dishes.
It deliberately includes things that must stay **hidden** on the public pages:
one pending restaurant, one unavailable dish, and one dish in an inactive
category. After seeding, the public pages should show **6 restaurants** and
**32 dishes**.

---

## 3.3 Phases 7-10: dashboards and operations

The current source includes customer dashboard summaries (`GET /api/dashboard/customer`), Super Admin approval/user APIs (`/api/admin/*`), Restaurant Admin menu/order management (`/api/restaurant-admin/*`), staff order progression (`/api/staff/*`), delivery assignment/status updates (`/api/delivery/*`), public and restaurant-managed offers (`/api/offers` and `/api/restaurant-admin/offers`), customer feedback (`/api/feedback`), notifications (`/api/notifications`), and a Food Memory timeline (`/api/food-memory/timeline`). These features are coded. Your recent local test report indicated the full pytest suite passed before the latest validation-policy change; rerun it after applying this validation update. Browser workflows still require manual verification.

Before using Phase 7-10 features on an existing database, take a backup and review `database/migrations/004_operations_engagement.sql`. It adds `delivery_partner_id`, `offer_id`, and `discount_amount` to `orders`, with foreign keys for delivery assignment and offers. The migration is additive; it does not delete orders or other records. Apply it once, after reviewing the target schema. Do not apply the migration blindly to a database that might already contain these columns.

An offer is accepted at checkout only when it is active, within its date range, and belongs to the restaurant in the cart. The backend computes the discount and final total; frontend totals are only a preview. Cash on Delivery remains the only payment method.

## 4. Run the tests

```powershell
cd C:\Users\Hello\Desktop\fooddna18
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

The tests create and use a **separate database** named `fooddna_test`
(dropped and rebuilt from `database/schema.sql` + the migrations on every
run). Your real `fooddna` and `fooddna_dev` data is never touched, and the
tests refuse to run if the test database name could collide with it. The MySQL
user in `.env` needs permission to create databases (`root` does).

Test files:

| File | Covers |
|---|---|
| `tests/test_foundation.py` | app start, DB connection, schema agreement (Phase 2) |
| `tests/test_auth.py` | registration, login, sessions, CSRF, password reset, applications (Phase 3) |
| `tests/test_rbac_and_cors.py` | role checks and CORS (Phase 3) |
| `tests/test_validation.py` | Unicode letters/spaces-only names and Gmail-only new-account emails |
| `tests/test_browsing.py` | restaurant, category and meal APIs: visibility, search, filters, price, sort, pagination, bad input (Phase 4) |
| `tests/test_seed.py` | seed script and dev-database initialiser safety (Phase 4) |
| `tests/test_preferences.py` | preferences API: create, update, validation, no duplicates, cannot touch another user's row, CSRF, roles (Phase 5) |
| `tests/test_recommendations.py` | scoring and ranking, budget / dietary / food-type filters, hidden meals, no-preference and empty results, history, selection (Phase 5) |
| `tests/test_food_memory.py` | Food Memory service, event validation and user scoping (Phase 5) |
| `tests/test_cart.py` | cart quantity, restaurant-conflict, ownership, availability, Food Memory and CSRF behavior (Phase 6) |
| `tests/test_orders.py` | checkout, authoritative price/totals, transaction rollback, COD, order history/detail access and cart clearing (Phase 6) |
| `tests/test_operations.py` | customer dashboard, approval flow, Super Admin operations and new-account validation (Phases 7–9) |
| `tests/test_engagement.py` | offers, feedback, notifications and Food Memory engagement (Phase 10) |

Please send me the final line of the pytest output (for example
`NNN passed`) and any failure text. The complete suite was reported passing locally before the latest validation-policy updates. Rerun it after any code or test changes; see section 7 for the evidence and remaining manual checks.

### 4.1 Optional: browser checks against a stand-in API

`tests/frontend/mock_browser_check.js` (Phase 4 pages) and
`tests/frontend/mock_phase5_check.js` (preferences and recommendations pages)
open the real pages in headless Chromium against a small **stand-in API** (not
Flask, not MySQL) and check the page behaviour. They are developer
conveniences, not a replacement for sections 5 and 5.1. Both start servers on
ports 5000 and 5500, so stop your real backend and `http.server` first and run
them one after the other.

```powershell
cd tests\frontend
npm install
npx playwright install chromium
node mock_browser_check.js
node mock_phase5_check.js
```

---

## 5. Manual browser testing (Chrome on Windows)

Do this once after section 3. Use two PowerShell windows as in section 2, but
start the backend with `$env:DB_NAME = "fooddna_dev"` first (section 3.1).
Open <http://127.0.0.1:5500/index.html> in Chrome. Press **F12** to open
DevTools; keep the **Console** tab visible and note any red errors.

| # | Do this | Expected result |
|---|---|---|
| 1 | Open `index.html` | Food DNA home page with **Browse restaurants** and **Browse food menu** buttons; navbar shows Home, Restaurants, Food Menu, Log in, Register |
| 2 | Click **Restaurants** | 6 restaurant cards (no "Pending Kitchen"); each shows description, address, "N dishes available" |
| 3 | Type `dragon` in the search box, press Search | Only *Demo Dragon Wok*. Search `zzzz`: message "No restaurants match your search" with a **Clear search** button |
| 4 | Clear the search, click **View menu** on *Demo Spice Garden* | Restaurant header (name, address, phone empty is fine) and 7 dishes; the unavailable "Seasonal Special Curry" is not shown |
| 5 | Click **Food Menu** | "32 dishes found", 12 cards per page, each with price in rupees, veg/non-veg badge, tags |
| 6 | Type `paneer` in Search dishes, click Apply | Only Paneer Tikka. Try `100%` or `_`: no matches (wildcards are treated as plain text) |
| 7 | Choose cuisine **Chinese**; then category **Starters**; then Min `150` Max `200`; then Sort **Price: high to low** | Results narrow each time; prices stay inside 150-200; order is high to low; the address bar updates with the filters |
| 8 | Search `zzzznothing` | "No dishes match your search" and **Clear all filters**; clicking it restores the full list |
| 9 | Enter Min `500`, Max `100`, Apply | Yellow warning "Minimum price cannot be greater than maximum price"; the list does not change. Try Min `abc`: "Prices must be positive numbers..." |
| 10 | Clear filters; click **Next** under the cards | "Page 2 of 3"; different dishes; address bar shows `page=2`. **Previous** goes back. Press Chrome Back/Forward and Refresh: the page and filters are kept |
| 11 | Click any dish name | Meal details: name, price, description, taste, spice, portion, dietary, cuisine, restaurant name and address; **View restaurant menu** and **Back to food menu** links work |
| 12 | Edit the address to `meal.html?id=abc` and then `meal.html?id=9999` | "Dish not found" both times, no crash |
| 13 | Press **Ctrl+Shift+M** (device toolbar) and choose a phone width (e.g. 375 px) | Navbar collapses behind a menu button that opens/closes; cards stack in one column; filter fields stack; no sideways scrolling |
| 14 | In the backend window press **Ctrl+C** (stop Flask), then open Restaurants and Food Menu | Red message "Cannot reach the server. Make sure the Flask backend is running on port 5000." with a **Try again** button. Restart Flask and click **Try again**: the data appears |
| 15 | Phase 3 regression: open Register, enter name `José García`, email `jose@gmail.com`, a strong password and matching confirmation. Then log out and log in. Also try Forgot password and the Restaurant Admin application page using a Gmail account address. | Registration/application succeeds; login, dashboard and logout work; reset flow shows the development link. |
| 16 | Type/paste `Asha 123`, `Rushi-Sharma`, or `O'Brien` in a new-account full-name field. Try `rushi@yahoo.com`, `rushi@gmail.co`, and `rushi@gmail.com.evil` in the account-email field. | Unsupported name characters are removed while typing/pasting; backend validation rejects tampered invalid names. Non-Gmail account domains are rejected and no account is created. |

### 5.1 Manual testing: preferences and recommendations (Phase 5)

Prerequisite: backend running against `fooddna_dev` with the demo data
(section 3.1), frontend on port 5500. Register a **new customer** (a fresh
account has no preferences) and log in. Keep DevTools open.

| # | Do this | Expected result |
|---|---|---|
| 1 | Look at the navbar | **Recommendations** and **My Preferences** links appear (customers only); the dashboard has two matching buttons |
| 2 | Open **Recommendations** before saving anything | "Tell us what you like" with a **Set my preferences** button; no dish cards; no error |
| 3 | Open **My Preferences** | Form with 7 dropdowns (filled from the demo data, including Taste and Portion) and a Budget box; note "You have not saved any preferences yet." |
| 4 | Choose Cuisine **North Indian**, Taste **Spicy**, leave the rest, Save | Green "Your preferences were saved." and a **See my recommendations** button. Reload the page: the same values are selected and "Last saved" shows a time |
| 5 | Type Budget `abc`, `0`, `-5`, `12.345`, then Save each time | Red message under the Budget box; nothing is saved (check the DevTools Network tab: no PUT request) |
| 6 | Open **Recommendations** | Dish cards ranked #1, #2, ... each with a "NN% match" badge, a "Why it matches" list, restaurant and price. Dishes from the pending restaurant, the unavailable curry and the inactive-category sundae never appear |
| 7 | Set Food type **Veg**, Save, open Recommendations | No Non-Veg dish appears. Set Food type **Non-Veg** instead: vegetarian dishes still appear, Non-Veg ones rank higher |
| 8 | Set Budget `150` (Cuisine North Indian), Save, open Recommendations | Every price is 150 or less; a grey note says how many dishes were hidden because of the budget |
| 9 | Set Dietary preference **Vegan** and Budget `1`, Save, open Recommendations | "No matching dishes right now" with a message and **Change my preferences**; no crash |
| 10 | Back on Recommendations change **How many** to 5, then press **Refresh** | The list reloads each time and shows at most 5 dishes |
| 11 | Scroll to **Recommendation history** | A table of what was recommended (time, dish, restaurant, match %). Refreshing within an hour does not add duplicate rows |
| 12 | Click a recommended dish name | The dish page opens normally |
| 13 | In MySQL: `SELECT user_id, meal_id, score, LEFT(reason,60) FROM recommendations;` and `SELECT user_id, meal_id, event_type, event_data FROM food_memory;` | Rows exist only for your user; `food_memory` has `recommendations_viewed`, `recommendation_selected` and `meal_viewed` events, with no passwords or emails |
| 14 | `SELECT COUNT(*) FROM user_preferences WHERE user_id = <your id>;` after saving several times | Exactly 1 |
| 15 | Log out and open `preferences.html` or `recommendations.html` | Sent to the login page |
| 16 | Log in as the Super Admin and open `preferences.html` | "Food preferences are available to customer accounts only." |

---

## 6. Project status

### Registration validation policy

- Account full names accept Unicode letters and spaces only. The customer registration, Restaurant Admin application, and Super Admin-created staff/delivery forms remove invalid name characters while typing or pasting; the backend rejects invalid values independently.
- New account email addresses must end with the exact `@gmail.com` domain. Other providers, incomplete domains (`@gmail.co`), and lookalike suffixes (`@gmail.com.evil`) are rejected on the client and server.
- The Gmail-only rule applies to new account creation, not login or password reset lookups, to avoid locking out pre-existing accounts. The optional restaurant contact-email field is distinct from the account email.


| Area | State |
|---|---|
| Flask app, config, DB connection, health endpoints | Built; tested in Phase 3 |
| Customer registration / login / logout / sessions / CSRF | Built; tested in Phase 3 |
| Password reset (hashed tokens, expiry, single use) | Built; tested in Phase 3 |
| Restaurant Admin application + status check | Built; tested in Phase 3 |
| Role-based access decorator (`role_required`) | Built; tested in Phase 3 |
| New account validation: Unicode letters/spaces-only names and exact `@gmail.com` domain, frontend and backend | Updated; syntax and isolated validation samples passed during packaging; complete tests must be rerun after this latest change |
| Restaurant list / details API | Built; **not yet run against MySQL** |
| Food category API | Built; **not yet run against MySQL** |
| Meal list / details API with search, cuisine/category/restaurant/food-type/dietary/spice filters, min/max price, sorting, pagination | Built; **not yet run against MySQL** |
| Pages: home, restaurants, restaurant menu, food menu, meal details | Built; run in headless Chromium against a stand-in API (13/13 passed); **not yet clicked through against real Flask + MySQL** |
| `init_dev_database.py` and `seed_demo_data.py` (separate `fooddna_dev`) | Built; guard logic and data checked statically; **not yet run against MySQL** |
| Auth frontend pages (Phase 3) | Load without JavaScript errors in headless Chromium; **not yet clicked through in a real browser** |
| Preferences API (get / create / update, one row per customer, validation) | Built; **not yet run against MySQL** |
| Recommendation scorer (budget, veg/vegan, dietary hard filters; weighted soft preferences; explanations), recommendation history | Built; scoring and validation logic smoke-checked in isolation (section 7); **not yet run against MySQL** |
| Food Memory service and events (`meal_viewed`, `recommendations_viewed`, `recommendation_selected`) | Built; **not yet run against MySQL** |
| Pages: preferences, recommendations (+ history) | Built; run in headless Chromium against a **stand-in API** (16/16 passed); **not yet clicked through against real Flask + MySQL** |
| Cart, orders, payments | Built in Phase 6; automated and MySQL integration tests still required |
| Customer dashboard | Built in Phase 7; API and role-aware dashboard added, not integration-tested |
| Super Admin approvals / account operations | Built in Phase 8; approval and operator APIs added, not integration-tested |
| Restaurant Admin / Staff workflow | Built in Phases 8-9; menu management and order state progression added |
| Delivery partner workflow | Built in Phase 9; claim/transition APIs use migration 004 |
| Feedback, offers, notifications, Food Memory timeline | Built in Phase 10; features added, not integration-tested |
| Full end-to-end testing and final package | Prepared in Phase 11-12; must run on the configured MySQL environment before claiming verified completion |

A database table does not count as a finished feature.

---

## 7. Verification status (read this first)

The Phase 4 work was rebuilt in an environment with **no network access, no
MySQL/MariaDB server, and without Flask-SQLAlchemy, PyMySQL or pytest
installed**. So:

**Actually executed:**

- Python syntax compilation of all 29 `.py` files (passed).
- Static check that every relative import in `backend/app` resolves to a real
  name (57 names, no problems) and that all six new API routes are registered.
- Node syntax check of `api.js`, `browse.js`, `layout.js` (passed).
- Dead-link and element-id check of all 12 HTML pages (93 checks, no problems).
- The new email and name rules, tested in Python and in Node on sample inputs
  (they agree).
- The seed data table (9 categories, 7 restaurants, 35 dishes, 32 publicly
  visible) and the seed safety guard (`validate_target`) with sample inputs.
- `tests/frontend/mock_browser_check.js`: the real pages in headless Chromium
  141 against a **stand-in API**: **13 passed, 0 failed**. Breaking the filter
  wiring on purpose made 3 of them fail, then restoring it made all pass.
  Bootstrap's stylesheet comes from a CDN that was unreachable, so visual
  layout and responsiveness were **not** judged.

**Phase 5 (preferences and recommendations), actually executed:**

- `py_compile` of every `.py` file, including the new services, routes and
  tests; `node --check` of all JavaScript; a dead-link / duplicate-id /
  required-id check of the HTML pages (no problems).
- The pure scoring and validation functions (`PreferenceProfile`,
  `failed_hard_rule`, `score_meal`, `rank_meals`, `validate_preferences`) run
  in isolation with the database layer replaced by stubs: 41 checks passed
  (ranking, tie-breaks, budget edge, veg/vegan/dietary rules, 50% spice
  credit, input validation). This does **not** exercise Flask, SQLAlchemy or
  MySQL.
- `tests/frontend/mock_phase5_check.js`: the real preferences and
  recommendations pages in headless Chromium 141 against a **stand-in API**:
  **16 passed, 0 failed**. Deliberately removing the CSRF header and switching
  to `innerHTML` made 5 of them fail; restoring the code made all pass. The
  Phase 4 stand-in check was re-run afterwards: 13 passed (no regression).

**NOT verified (needs your PC):**

- All Phase 5 pytest files (`test_preferences.py`, `test_recommendations.py`,
  `test_food_memory.py`): written and compiled, **never executed**. Their
  expectations could contain mistakes.
- Phase 5 SQL on MySQL (the joins in `list_history`, `JSON` event data, the
  `UNIQUE(user_id)` race fallback) and every API response against a running
  Flask server.
- The Phase 5 manual checklist (section 5.1).

- `python -m pytest -q`: the new test files (`test_validation.py`,
  `test_browsing.py`, `test_seed.py`) compile but were **never executed**, and
  no test results from the earlier conversation apply to these files.
  Phase 3 tests were not re-run either.
- The SQL that SQLAlchemy generates (joins, subqueries, `LIKE ... ESCAPE`,
  `DISTINCT`) on MySQL. The earlier conversation's log reports the same logic
  working on MariaDB 10.11; that is not a result for these files.
- `init_dev_database.py` and `seed_demo_data.py` against a real server.
- Everything in section 5 against real Flask + MySQL in Chrome.
- Behaviour on Oracle MySQL 8.

---

## 8. API reference

All responses are JSON: `{"success": true|false, ...}`. Requests that change
data and use the session cookie must send the `X-CSRF-Token` header (returned
by `POST /api/auth/login`, or fetch it from `GET /api/auth/csrf`).

### Authentication and health (Phase 2-3)

| Method | URL | Auth | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/health` | - | Server is up | 200 |
| GET | `/api/health/db` | - | MySQL reachable | 200, 503 |
| POST | `/api/auth/register` | - | Create a customer | 201, 400 invalid, 409 email exists |
| POST | `/api/auth/restaurant-admin/apply` | - | Submit restaurant application | 201, 400, 409 |
| POST | `/api/auth/login` | - | `email`, `password`, `role`, `remember_me` | 200, 401 bad login, 403 wrong role / pending / rejected / suspended, 429 too many attempts |
| GET | `/api/auth/me` | login | Current user | 200, 401 |
| GET | `/api/auth/csrf` | login | CSRF token | 200, 401 |
| POST | `/api/auth/logout` | login + CSRF | End session | 200, 401, 403 |
| GET | `/api/auth/application-status` | login | Own application (logged-in users) | 200, 404 |
| POST | `/api/auth/application-status/check` | email + password | Applicant checks status without logging in | 200, 401, 404, 429 |
| POST | `/api/auth/forgot-password` | - | `email`. Same reply whether or not the account exists | 200, 400 |
| POST | `/api/auth/reset-password` | - | `token`, `password`, `confirm_password` | 200, 400 |

### Browsing (Phase 4, public, read-only, no login needed)

| Method | URL | Purpose | Status codes |
|---|---|---|---|
| GET | `/api/restaurants` | Approved restaurants. Query: `q` (name search), `page`, `page_size` (default 12, max 50). Each item has `meal_count` (visible dishes) | 200, 400 |
| GET | `/api/restaurants/<id>` | One approved restaurant (adds `phone`) | 200, 400 bad id, 404 not found or not approved |
| GET | `/api/categories` | Active categories with `meal_count` | 200 |
| GET | `/api/meals` | Visible meals. Query: `q` (name/description), `restaurant_id`, `category_id`, `cuisine`, `meal_type`, `food_type`, `dietary_preference`, `spice_level`, `min_price`, `max_price`, `sort` (`name` \| `price_asc` \| `price_desc`), `page`, `page_size` | 200, 400 |
| GET | `/api/meals/filters` | Distinct filter values and price range among visible meals (feeds the dropdowns) | 200 |
| GET | `/api/meals/<id>` | One visible meal with restaurant name and address | 200, 400 bad id, 404 not found or hidden |

Rules:

- A meal is **visible** only if it is available, its category is active, and
  its restaurant status is `approved`. Everything comes from the database.
- Prices are plain numbers with at most 2 decimals; `min_price` greater than
  `max_price`, negatives, exponents, over-long text and bad ids give `400`
  `{"success": false, "error": "..."}`.
- Search text is matched literally (`%` and `_` are escaped) and always sent to
  MySQL as parameters, never pasted into SQL.
- An empty result is `200` with an empty list. List responses include
  `pagination: {page, page_size, total, total_pages}`.
- Only `http(s)` image links are returned (`javascript:` links become `null`).

### Preferences, recommendations and Food Memory (Phase 5, customers only)

All of these need a logged-in **customer** (other roles get `403`, anonymous
visitors `401`). The user is always the session user; a `user_id` in the
query or body is ignored. `PUT`/`POST` also need the `X-CSRF-Token` header.

| Method | URL | Purpose | Status codes |
|---|---|---|---|
| GET | `/api/preferences` | Saved preferences (`preferences` is `null` if never saved) and `has_preferences` | 200, 401, 403 |
| PUT | `/api/preferences` | Create **or** replace the preferences. Body = the complete set: `cuisine`, `meal_type`, `taste`, `spice_level`, `portion_size`, `food_type`, `dietary_preference` (text) and `budget` (number > 0, max 2 decimals). Missing / null / blank = no preference. Unknown keys are ignored. Reply has `created` | 201 created, 200 updated, 400 (`errors` per field, or body not a JSON object), 401, 403 |
| GET | `/api/recommendations?limit=10` | Compute recommendations. **Writes nothing.** `limit` 1-30 (default 10) | 200, 400, 401, 403 |
| POST | `/api/recommendations` | Same result, **and** records history in `recommendations` plus a `recommendations_viewed` event. Optional body `{"limit": 10}`. The pages use this | 200, 400, 401, 403 |
| GET | `/api/recommendations/history?page=&page_size=` | The customer's own past recommendations (newest first) with `currently_available` | 200, 400, 401, 403 |
| POST | `/api/recommendations/<meal_id>/select` | Record that the customer opened a recommended meal. Only meals recommended to **this** customer and still visible | 200 (`recorded`), 400, 401, 403, 404 |
| POST | `/api/food-memory/meal-views` | Body `{"meal_id": 12}`: record a meal-page view (visible meals only; repeats within 30 min are skipped) | 200 (`recorded`), 400, 401, 403, 404 |

A recommendation item: `rank`, `score` (0-100 as text), `matched` and `partial`
(preference names), `reasons` (sentences), and `meal` (same shape as
`GET /api/meals`). The top level also has `has_preferences`, `preferences` (the
ones in use), `message` (set when the list is empty) and `summary`
(`visible_meals`, `excluded` counts per rule, `no_match`, `returned`, `limit`).
A customer with no preferences, or with no matching meals, gets `200` with an
empty list and an explanatory `message`; it is not an error.

`GET /api/meals/filters` also returns `tastes` and `portion_sizes` now (used
by the preference form).

**How scoring works, in short** (full detail and limitations in
`docs/RECOMMENDATIONS.md`): meals the Phase 4 pages show are first filtered by
three **hard rules** (budget = maximum price per dish, Veg/Vegan food type,
dietary preference), then scored by the weighted share of the customer's other
preferences they match (cuisine 20, meal type 15, taste 15, spice 15,
portion 10, food type 10, dietary 10, budget 5; spice one step away earns half).
### Shopping Cart and Ordering (Phase 6, customers only)

All cart and ordering endpoints require a logged-in **customer** (`role_required("customer")`). The authenticated customer is derived securely from the server session. Mutating requests require the `X-CSRF-Token` header.

| Method | URL | Auth | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/cart` | customer | Retrieve customer's active cart, items, line totals, subtotal, delivery fee and total | 200, 401, 403 |
| POST | `/api/cart/items` | customer + CSRF | Add an available dish (`meal_id`, optional `quantity`). If the dish is already in the cart, increments quantity. Enforces one restaurant per cart: returns 409 if adding from another restaurant | 200, 400 (bad id/quantity/unavailable), 401, 403, 409 (restaurant conflict) |
| PATCH | `/api/cart/items/<id>` | customer + CSRF | Update quantity for a specific line item in the customer's cart (`{"quantity": 1..50}`) | 200, 400, 401, 403, 404 |
| DELETE | `/api/cart/items/<id>` | customer + CSRF | Remove an individual item from the customer's cart | 200, 401, 403, 404 |
| DELETE | `/api/cart` | customer + CSRF | Clear all items from the customer's cart (preserves the customer's Cart row) | 200, 401, 403 |
| POST | `/api/orders` | customer + CSRF | Checkout / Place order. Body: `{"delivery_address": "...", "payment_method": "cash_on_delivery", "offer_id": 123}` (optional offer). Revalidates all dishes and prices, computes totals using Decimal arithmetic, atomically saves Order, OrderItems, OrderStatusHistory and Payment ('pending' Cash on Delivery), records Food Memory `order_placed` event, and clears the cart | 201 created, 400 (empty cart/invalid address/validation error), 401, 403, 500 |
| GET | `/api/orders` | customer | Paginated order history (newest first) with restaurant name, date, items summary, status and total | 200, 400, 401, 403 |
| GET | `/api/orders/<id>` | customer | Full details for an order belonging to the customer: dishes, unit prices, line totals, address, status timeline, and payment info | 200, 400, 401, 403, 404 |
| GET | `/api/orders/<id>/status` | customer | Current order status and status-history timeline | 200, 400, 401, 403, 404 |

**Phase 6 Rules:**
- **One restaurant per cart:** A cart can only contain dishes from a single restaurant at a time. If an item from a different restaurant is added, the server returns HTTP 409 (`RESTAURANT_CONFLICT`), and the frontend offers a prompt to clear the cart and switch restaurants.
- **Server-authoritative pricing:** Prices and totals are computed strictly from current MySQL database values using Python `Decimal` arithmetic. Client-supplied totals are rejected/ignored.
- **Cash on Delivery (COD) only:** Initial payment workflow creates a `Payment` record with status `"pending"`. No external payment gateways are fabricated.
- **Transactional integrity:** Order, OrderItems, OrderStatusHistory, Payment, and Food Memory records are created atomically; if any step fails, the entire transaction rolls back and the cart is preserved.
- **Cart persistence:** Clearing the cart deletes `CartItem` rows but keeps the `Cart` row, preventing constraint violations on `UNIQUE(user_id)`.

### Development vs production

- With `FLASK_ENV=development`, `forgot-password` returns a
  `development_reset_url`, because **no email service is configured**.
  In production it is never returned; an email sender must be added.
- `SESSION_COOKIE_SECURE` must be `1` behind HTTPS in production.
- Production refuses to start with a missing/placeholder `SECRET_KEY`.
- CORS only allows the origins in `CORS_ORIGINS` (never `*`, never `null`).

---

## 9. Known limitations (current)

- Phase 4 and Phase 5 tests and real-browser testing are **not yet verified**
  (section 7).
- Recommendations are rule-based and use saved preferences. Food Memory events are stored for a later ranking improvement; current scoring does not automatically use all events. Feedback endpoints are now included, but feedback-driven ranking is not yet implemented.
- Dietary labels are free text set by restaurants. When a customer sets a
  dietary preference, dishes without a dietary label are hidden because their
  suitability cannot be shown.
- The scorer ranks the whole visible catalogue in Python on every request;
  fine for demo-sized data, to be revisited for thousands of dishes.
- `recommendations` and `food_memory` grow with use; there is no clean-up job.
- Two simultaneous recommendation requests could still insert the same
  (customer, meal) row twice (no unique constraint, by design: history).
- Restaurants become public only when their `status` is `approved`; the Super Admin approval workflow is included in the current code but has not yet been integration-tested.
- Restaurants have no image or cuisine column, so restaurant cards show text
  only; meals use a letter tile when `image_url` is empty.
- Search is simple substring matching (`LIKE`), not full-text or fuzzy search.
- Prices display with the rupee sign (`CURRENCY_SYMBOL` in `frontend/js/api.js`).
- New account names accept Unicode letters and spaces only. New account email addresses must use the exact `@gmail.com` domain. Existing accounts can still sign in with their stored email address; the Gmail-only rule is enforced when creating new account records. Optional restaurant contact email is a separate field and remains a normal email address.
- Login lockout is per-process memory (fine for one dev server; use a shared
  store such as Redis with several workers).
- Existing sessions are not revoked when a password is reset.
- No real email delivery and no real payment gateway.
- Automated tests from earlier phases ran on MariaDB 10.11 (MySQL-compatible),
  not on Oracle MySQL; run `python -m pytest -q` on your machine to confirm.
