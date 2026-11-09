# FoodDNA - Project Audit

Audit date: 12 Oct 2026. Source of truth: the uploaded `fooddna18.zip`.
Every "verified" statement below was observed by running the code (the original,
unmodified files for the findings in section E) against a real SQL server built
from `database/schema.sql` + migrations. "Not verified" means exactly that.

Environment used for verification: Python 3.12, MariaDB 10.11 (MySQL-compatible,
**not** Oracle MySQL), Flask 3.1.2. No real browser was available.

> **Note:** the paragraphs above and sections 1-4 describe the Phase 1-3 audit and
> its environment. The **Phase 4 update** below was produced in a different
> environment (no database server, no pytest) and states separately what was and
> was not verified.


## Current archive update (12 Oct 2026)

The uploaded project archive contains Phases 1-6. This working copy adds initial Phase 7-10 API and interface coverage: role dashboards, Super Admin approval/account operations, Restaurant Admin menu/order/offer management, staff order progression, delivery claiming/status updates, customer feedback, notifications, and an offer-aware checkout. Migration `004_operations_engagement.sql` is additive. Python and JavaScript syntax checks are run during packaging; a Flask/MySQL integration run is not possible in this environment because Flask, Flask-SQLAlchemy, Flask-Cors and PyMySQL are not installed and no MySQL service is available. Treat Phase 7-10 as implemented but unverified until `python -m pytest -q` and the real browser checklist run on the configured development/test database.

## Phase 4 update (food and restaurant browsing)

Phase 4 was **reconstructed** from `fooddna18_phase3.zip` plus the progress log
of an earlier conversation. The Phase 4 files from that conversation were not
available (the log's code had its line breaks flattened), so every Phase 4 file
was rewritten from the log's descriptions and code. Nothing was copied from a
file that was not actually present.

### Added or changed

| Area | Files |
|---|---|
| Query validation | `backend/app/utils/query_params.py` (new) |
| Services | `backend/app/services/restaurant_service.py`, `meal_service.py` (new) |
| Routes | `backend/app/routes/restaurants.py`, `meals.py` (new); both registered in `backend/app/__init__.py` |
| Validation | `backend/app/utils/validation.py`, `frontend/js/api.js`, `register.html`, `restaurant-admin-application.html`, `create_super_admin.py` (finding F1 resolved) |
| Dev database | `backend/init_dev_database.py`, `backend/seed_demo_data.py` (new) |
| Frontend | `frontend/js/browse.js` (new), `frontend/js/layout.js` (responsive navbar), `api.js` (browse helpers), `css/style.css`, `index.html`; pages `restaurants.html`, `restaurant-menu.html`, `menu.html`, `meal.html` (new) |
| Tests | `tests/test_validation.py`, `tests/test_browsing.py`, `tests/test_seed.py` (new); `tests/frontend/mock_browser_check.js` (optional developer tool) |
| Docs | `README.md`, this file |

No database migration was added; the existing `restaurants`, `food_categories`
and `meals` tables are used as they are. `requirements.txt` is unchanged.

### Design decisions

- **Visibility rule:** a meal is public only if `meals.is_available`, its
  category `is_active`, and its restaurant `status = 'approved'`. A restaurant is
  public only if `approved`. Pending/rejected restaurants return 404 on detail.
- **No hard-coded data in the frontend:** filter dropdowns come from
  `GET /api/meals/filters` and `GET /api/categories`.
- **All SQL goes through SQLAlchemy with bound parameters;** `LIKE` wildcards
  in user text are escaped.
- **All server text is inserted with `textContent`**, never `innerHTML`.
- **Dev data is separate:** the seed refuses `fooddna`, refuses non-`_dev`
  names, requires `FLASK_ENV=development`, only inserts, and is never imported
  by the app.

### What was actually executed for Phase 4

Environment: Python 3.12, Node, headless Chromium 141 (Playwright). **No MySQL
or MariaDB server, no network, and Flask-SQLAlchemy / PyMySQL / pytest were not
installed.**

| Check | Result |
|---|---|
| `py_compile` of all 29 `.py` files | Passed |
| Relative-import resolution in `backend/app` (57 names) | No problems |
| All 6 new API routes registered, and frontend API paths match | Passed |
| `node --check` of `api.js`, `browse.js`, `layout.js`, `mock_browser_check.js` | Passed |
| Dead links / duplicate ids / required element ids in 12 HTML pages (93 checks) | No problems |
| New name and email rules in Python and in Node on sample inputs | Agree |
| Seed data integrity (9 / 7 / 35, 32 publicly visible) and `validate_target` on sample inputs | Passed |
| Real pages in headless Chromium against a **stand-in API** (`mock_browser_check.js`) | **13 passed, 0 failed.** Deliberately breaking the filter wiring made 3 fail |

The stand-in API is a small Node server written for this check. It is not
Flask and not MySQL, so these 13 results say nothing about the backend. The
Bootstrap stylesheet could not be downloaded (no network), so visual layout and
the responsive design were not judged.

### What is NOT verified

| Item | Status |
|---|---|
| `python -m pytest -q` (all test files, including the Phase 3 ones) | **NOT YET VERIFIED. No pytest result exists for this ZIP** |
| `test_validation.py`, `test_browsing.py`, `test_seed.py` | Written and compiled, **never executed**; their expectations could contain mistakes |
| The earlier log's "241 tests passed" | Applies to the earlier conversation's files only; **not** to this ZIP, and this ZIP has a different test set |
| Generated SQL (joins, subqueries, `LIKE ... ESCAPE`, `DISTINCT`) on MySQL | **NOT YET VERIFIED** (the log reports MariaDB 10.11 only) |
| `init_dev_database.py` / `seed_demo_data.py` against a real server | **NOT YET VERIFIED** |
| Manual testing in Chrome against real Flask + MySQL (README section 5) | **NOT YET VERIFIED** |
| Responsive layout, Bootstrap styling | **NOT YET VERIFIED** |
| Phase 3 pages clicked through in a real browser | **NOT YET VERIFIED** |
| Oracle MySQL 8 | **NOT YET VERIFIED** |

The Phase 3 suite (74 tests in the Phase 3 audit) was not re-run for this ZIP.
Existing authentication, CSRF, RBAC and database-safety tests were not edited
or weakened; only the validation rules they relied on were relaxed, and none of
the existing assertions depended on `.com` or ASCII-only names.

### Known limitations (Phase 4)

- Public pages are empty on the real `fooddna` database until restaurants are
  approved (the approval screens are a later phase) and have meals.
- No restaurant images or cuisine column; letter tile when a meal has no image.
- Substring search only; no ranking, fuzzy matching or full-text index.
- Email addresses accept ASCII characters only (names are Unicode).
- Listing queries use `COUNT` plus `OFFSET`; fine for demo scale, to be revisited
  with large catalogues.

## Phase 5 update (preferences and personalised recommendations)

Built from the uploaded `fooddna18_phase4.zip` by inspecting the real models
(`UserPreference`, `Recommendation`, `FoodMemory`, `Meal`), the Phase 4
services and routes, `schema.sql` and the existing tests. Nothing was assumed
from table names alone: before this phase there were **no** preference,
recommendation or Food Memory routes or services (finding D in section 2).
Per the project owner's approach, this phase was **coded, not tested**: the
full pytest suite was not run.

### Added or changed

| Area | Files |
|---|---|
| Services | `backend/app/services/preference_service.py`, `recommendation_service.py`, `food_memory_service.py` (new); `meal_service.py` (additive: `visible_meal_rows()`, and `tastes` / `portion_sizes` in `get_filter_options()`) |
| Routes | `backend/app/routes/preferences.py`, `recommendations.py`, `food_memory.py` (new); registered in `backend/app/__init__.py` |
| Frontend | `preferences.html`, `recommendations.html`, `js/preferences.js`, `js/recommendations.js` (new); `js/api.js` (Phase 5 helpers), `js/layout.js` (customer nav links), `js/browse.js` (meal-view event), `dashboard.html`, `css/style.css` |
| Tests (written, not run) | `tests/test_preferences.py`, `test_recommendations.py`, `test_food_memory.py`; optional `tests/frontend/mock_phase5_check.js` |
| Docs | `README.md`, `docs/RECOMMENDATIONS.md`, `docs/PHASE5_PROGRESS.md`, this file |

**No database migration.** The three tables already hold everything needed:
`user_preferences` has `UNIQUE(user_id)` (one row per customer),
`recommendations` has score / reason / generated_at, `food_memory` has
event_type and JSON event_data. No column or table was changed or dropped.
`requirements.txt` is unchanged.

### Design decisions

- **Customers only.** All new endpoints use `role_required("customer")`; the
  user id always comes from the session, never from the request.
- **Transparent scoring** with documented weights (`docs/RECOMMENDATIONS.md`);
  budget, Veg/Vegan food type and dietary preference are hard filters; other
  attributes are weighted soft matches; missing optional data never rejects a
  meal by itself.
- **Phase 4 visibility is reused**, not copied: the scorer reads meals through
  `meal_service.visible_meal_rows()`, which uses the same filter as browsing.
- **`GET /api/recommendations` is side-effect free**; `POST` records history
  (CSRF-protected). Repeats within 60 minutes refresh the existing row.
- **`PUT /api/preferences` replaces the whole set** and rejects a body that is
  not a JSON object, so a malformed request can never wipe a customer's data.
- **Food Memory** is a single reusable `record_event` with a registry of
  allowed event types and per-type duplicate windows; only events the app can
  record today are registered. The cart and ordering events are left for Phase 6.

### What was actually executed for Phase 5

Environment: Python 3.13, Node, headless Chromium 141 (Playwright). **No
MySQL/MariaDB, no network for pip, and Flask / Flask-SQLAlchemy / PyMySQL /
pytest were not installed.**

| Check | Result |
|---|---|
| `py_compile` of all `.py` files (including the 3 new test files) | Passed |
| `node --check` of all JavaScript | Passed |
| Dead links, duplicate ids and required element ids in the HTML pages | No problems |
| Pure scoring / validation functions with the DB layer stubbed (41 checks) | 41 passed, 0 failed |
| `mock_phase5_check.js`: real pages in headless Chromium against a **stand-in API** | **16 passed, 0 failed**; removing the CSRF header and using `innerHTML` made 5 fail, restoring made all pass |
| `mock_browser_check.js` (Phase 4 pages) re-run after the shared-file edits | 13 passed, 0 failed |

### What is NOT verified

| Item | Status |
|---|---|
| `python -m pytest -q` (all files) | **NOT YET VERIFIED** |
| `test_preferences.py`, `test_recommendations.py`, `test_food_memory.py` | Written and compiled, **never executed**; expectations may be wrong |
| SQL and responses of the new endpoints on MySQL / MariaDB via real Flask | **NOT YET VERIFIED** |
| Login as `restaurant_admin` in the role-refusal tests (they assume an approved user can log in) | **NOT YET VERIFIED** |
| README section 5.1 manual checklist in Chrome against real Flask + MySQL | **NOT YET VERIFIED** |
| Bootstrap layout / responsiveness of the new pages (CDN unreachable in the build environment) | **NOT YET VERIFIED** |

### Known limitations (Phase 5)

- Rule-based matching on exact (case-insensitive) text; free-text attribute
  labels can disagree (see `docs/RECOMMENDATIONS.md` section 6).
- Dishes without a dietary label are hidden for customers with a dietary preference.
- Food Memory is recorded but not yet used for ranking; no ratings/popularity yet.
- Whole visible catalogue is scored in memory per request.
- No clean-up of old `recommendations` / `food_memory` rows.
- The frontend allows letters/digits via `\p{L}\p{N}`, the backend via Python's
  `\w`; very unusual Unicode input could be accepted by one and refused by the
  other (the server's message is then shown).
- Phase 6 is implemented in the current archive (cart and ordering); testing remains deferred. The later Phase 7-10 implementation is documented below.

## 1. Inventory (what is actually in the ZIP)

| Area | Files | Lines |
|---|---|---|
| Backend app | `backend/app/{__init__,config,extensions,models}.py` | ~1,160 |
| Auth | `routes/auth.py`, `services/auth_service.py`, `middleware/auth.py`, `utils/validation.py` | ~940 |
| Scripts | `backend/run.py`, `backend/create_super_admin.py` | ~125 |
| Database | `database/schema.sql`, `migrations/001`, `002` | ~485 |
| Frontend | `frontend/index.html` only (a health-check button) | 128 |
| Tests | none | 0 |
| Docs | `README.md` (cut off mid-sentence) | 40 |

Only the authentication module has routes. There are **no** routes for food,
restaurants, preferences, recommendations, cart, orders, payments, feedback,
offers, notifications, staff, delivery or administration.

## 2. Findings by category

### A. Implemented and verified (original code)
- App factory starts; `/api/health` returns 200.
- `schema.sql` + both migrations apply cleanly: 24 tables, 5 roles
  (`customer, restaurant_admin, staff, delivery_partner, super_admin`).
- Customer registration (validation, password hashing, duplicate email).
- Login incl. wrong-role (403) and invalid credentials (401); `/me`; CSRF-protected
  logout; session cleared on logout.
- Restaurant Admin application creates user + restaurant + link + approval
  records, all `pending`; pending applicants cannot log in.
- `create_super_admin.py` creates the account and refuses a duplicate.
- `models.py` has exactly one `PasswordResetToken` (the suspected duplicate class
  is **not** present) and imports/parses cleanly.

### B. Implemented, not yet tested (before this work)
- Everything: the project had zero automated tests.

### C. Partially implemented
- Password reset: service logic was fine, but the route crashed (see E2) and no
  frontend page existed.
- Restaurant Admin flow: application and pending-state exist; no way to approve
  or reject (no Super Admin routes).
- Models for all other modules exist (24 tables) with no routes or services.

### D. Missing
(Original Phase 1 finding. Browsing was added in Phase 4 and preferences,
recommendation scoring and Food Memory events in Phase 5; none of the Phase 4-5
work is test-verified yet.)
Food/restaurant browsing, preferences, recommendation scoring, Food Memory events,
cart, ordering, status workflow, payments, dashboards, Super Admin / Restaurant
Admin / staff / delivery operations, feedback, offers, notifications, seed data,
tests, API docs, most frontend pages.

### E. Broken or inconsistent (E1-E4 reproduced on the original code; status after Phase 2/3)
| # | Finding | File | Severity | Status |
|---|---|---|---|---|
| E1 | `role_required` had a stray `@wraps` and did nothing: an anonymous user and a customer both got **200** on a "super_admin-only" route. No route used it yet, so nothing was exposed, but every future admin route would have been open. | `middleware/auth.py` | **Critical** | Fixed + tested (suite goes red if re-broken) |
| E2 | `forgot-password` crashed with `KeyError: 'ENV'` for any real account (`config["ENV"]` was removed in Flask 2.3+). Unknown emails worked, so the 500-vs-200 difference also revealed which emails exist. | `routes/auth.py` | High | Fixed + tested |
| E3 | Reset link pointed to `/pages/auth/reset-password.html`, which does not exist. | `routes/auth.py` | High | Fixed (`/reset-password.html`), page created |
| E4 | A pending/rejected applicant cannot log in, but the only status endpoint required login, so applicants could never see their status. | `routes/auth.py` | High | Fixed: new `POST /api/auth/application-status/check` |
| E5 | CORS allowed the `null` origin with credentials. | `__init__.py` | Medium | Removed; origins from config |
| E6 | Sessions stayed valid after an account became suspended/rejected (only `is_active` was re-checked). | `middleware/auth.py` | Medium | Fixed + tested |
| E7 | Two simultaneous registrations/applications with one email could return a raw 500 (`IntegrityError`). | `auth_service.py` | Medium | Fixed: 409 + rollback, tested sequentially (true concurrency not tested) |
| E8 | Reset token "unused" check was read-then-write (race). | `auth_service.py` | Medium | Fixed: atomic `UPDATE ... WHERE used_at IS NULL` (single-use tested; true concurrency not tested) |
| E9 | Non-string JSON (`{"email": ["x"]}`) could raise `AttributeError` (500). | routes/services | Medium | Fixed + tested |
| E10 | No brute-force protection on login. | `routes/auth.py` | Medium | Added per-IP+email lockout (in-memory) |
| E11 | Default `SECRET_KEY` fallback was a known string; `run.py` hard-coded `debug=True`; `SESSION_COOKIE_SECURE` hard-coded False. | `config.py`, `run.py` | Medium | Now env-driven; production refuses placeholder key |
| E12 | DB errors were unhandled; no JSON handler for 405. | `__init__.py` | Low | JSON handlers; real cause logged, safe message returned |
| E13 | README ends mid-sentence; no `pytest` in requirements. | docs | Low | Rewritten / added |

E5-E13 were found by reading the code; the fixes are covered by tests, but I
did not separately reproduce each original failure.

### F. Requires clarification (not changed)
1. **Validation policy changed on 16 Oct 2026:** the current requested policy is Unicode letters and spaces only for new account names and exact `@gmail.com` for new account email addresses. See the `Validation policy follow-up` below; it supersedes this historical Phase 4 entry.
2. **One order = one restaurant** (`orders.restaurant_id`), but a cart can hold
   meals from many restaurants. Proposed for Phase 6: a cart holds meals from one
   restaurant at a time.
3. **No `payment_status` on orders.** Payments live in `payments`. Proposed: a
   clearly labelled demo payment only, no card data.
4. **`cart_items` has no unique (cart_id, meal_id).** Needed to make "add the same
   meal twice" safe (new migration `003` in Phase 6).
5. Offers: `discount_percent` exists; decide whether Phase 10 applies it at checkout.

## 3. Security note about the ZIP you uploaded
The ZIP contained your real `.env` (MySQL password and `SECRET_KEY`). I did not
print or use those values. Please (a) not share that ZIP again, and (b) consider
changing your MySQL password and generating a new `SECRET_KEY`.

## 4. Verified results after Phase 2 + 3
- Automated tests: **74 written, 74 executed, 74 passed** (`python -m pytest -q`).
- Sanity check: re-breaking `role_required` makes the suite fail.
- Live check: the project's real `frontend/js/api.js` run in Node against the
  running Flask server: **24/24 passed** (register, duplicate, login, role
  mismatch, CSRF, logout, reset-link flow, pending applicant, backend-down message).
- CORS preflight from `http://127.0.0.1:5500`: allowed with credentials and
  `X-CSRF-Token`; an unknown origin gets no CORS headers.
- All 8 frontend pages: JavaScript syntax-checked, zero dead links.
- **Not verified:** pages clicked through in a real browser; behaviour on Oracle
  MySQL; email delivery (none exists).

## 5. Current completion and verification status

The percentage estimates in the earlier audit were made before Phases 7–10 were added, so they are not used as a current completion score. The current working archive contains implementation code for Phases 1–10, plus additional test cases and documentation for Phases 11–12. This does **not** mean the application is verified end-to-end.

| Area | Current state | Evidence / remaining work |
|---|---|---|
| Authentication and foundation | Implemented | Earlier Phase 2–3 tests were reported as passing; run the full suite again against the current archive. |
| Browsing and recommendations | Implemented | Routes, services, pages and tests are present; database-backed integration tests still required. |
| Cart and ordering | Implemented | APIs, services, pages and tests are present; test checkout transaction and migration 003 on the isolated test database. |
| Dashboards and administration | Implemented in this archive | Phase 7–8 routes/UI added; role checks and approval flow require integration testing. |
| Staff and delivery | Implemented in this archive | Phase 9 routes added; migration 004 and MySQL row-lock behaviour require verification. |
| Feedback, offers and notifications | Implemented in this archive | Phase 10 APIs/pages added; test offer math, data ownership and notifications. |
| Documentation and packaging | Prepared | README, audit, progress/test plans and secret-free archive included. |
| Testing | Not complete | Python/JavaScript syntax and local HTML references passed; pytest and live MySQL/browser checks were not run in this environment. |

## 6. Implementation plan
1. ~~Phase 1 Audit~~ done
2. ~~Phase 2 Foundation repair~~ done
3. ~~Phase 3 Authentication~~ done (customer + applicant)
4. Phase 4 Food & restaurant browsing (+ dev seed script, kept separate from real data): **built; run pytest and the README section 5 checklist to verify**
5. ~~Phase 5~~ Preferences + transparent scoring recommender (+ Recommendation records) + Food Memory service: **built; tests written, not run**
6. ~~Phase 6~~ Cart + ordering (migration 003, status workflow, demo payment): **built; tests written, not run**
7. Phase 7 Customer dashboard: **implemented; not integration-tested**
8. Phase 8 Super Admin approvals + Restaurant Admin management: **implemented in current working archive; tests not executed**
9. Phase 9 Staff + delivery: **implemented in current working archive; requires migration 004 and integration tests**
10. Phase 10 Feedback, offers, notifications, Food Memory timeline: **implemented in current working archive; tests not executed**
11. Phase 11 End-to-end tests + DB consistency checks: **test files updated, but full pytest/MySQL checks are not run in this environment**
12. Phase 12 Final docs and package: **documentation and clean archive prepared; live DB/browser verification remains**


## Validation policy follow-up (16 Oct 2026)

The original archive used a broader email rule and allowed apostrophes, hyphens, and periods in account names. This was changed to match the requested registration policy:

- New account full names accept Unicode letters and spaces only. Customer registration and Restaurant Admin application forms strip unsupported characters during typing/paste; backend validation remains authoritative. Super Admin's staff/delivery account form follows the same name rule.
- New account email addresses must use exactly `@gmail.com`, case-insensitively. Other providers, incomplete domain endings, repeated dots, and suffixes such as `gmail.com.evil` are rejected in both the frontend and backend.
- The rule applies when creating accounts. Existing users are not blocked from login/password reset solely because an older stored address is not Gmail. The optional restaurant contact email remains separate from the account login email.
- Super Admin-created staff/delivery accounts now use the same strong-password validator, in addition to the existing 10-character minimum.
- Updated the Python validation/auth tests and the frontend stand-in browser assertion to match the requested policy. Added a focused regression test for operator account creation.

**Verification status for this follow-up:** Python source syntax, JavaScript syntax, local HTML references, and isolated name/email validation cases were checked while preparing the archive. The full pytest suite and Playwright browser suite were not run in this build environment because Flask, Flask-SQLAlchemy, Flask-Cors, PyMySQL and the project-side browser dependencies are not installed here. The user reported that the previous full test suite passed before these validation changes; rerun the suite against the dedicated `*_test` database after applying this update.
