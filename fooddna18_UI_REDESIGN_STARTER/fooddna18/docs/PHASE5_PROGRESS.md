# FoodDNA - Phase 5 progress report

Phase 5: personalised FoodDNA recommendations (preferences, scoring,
recommendation history, Food Memory).

**Status: implemented. NOT tested against Flask and MySQL.** Testing is
deferred to the dedicated testing phase, as agreed. Nothing here has passed
`python -m pytest -q`.

## What was built

1. **User preferences** - `GET` / `PUT /api/preferences`; one row per customer
   (`UNIQUE(user_id)` plus an insert-race fallback), validation of every field
   and of `budget`, user taken from the session only, CSRF on `PUT`, customer
   role only. Frontend: `preferences.html` + `js/preferences.js`.
2. **Recommendation algorithm** - `services/recommendation_service.py`:
   hard filters (budget, Veg/Vegan, dietary), weighted soft scoring, ranking,
   explanations. Documented in `docs/RECOMMENDATIONS.md`.
3. **APIs** - `GET` / `POST /api/recommendations`, `GET /api/recommendations/history`,
   `POST /api/recommendations/<id>/select`, `POST /api/food-memory/meal-views`
   (table in `README.md` section 8).
4. **Recommendation history** - stored in the existing `recommendations`
   table; repeats within 60 minutes refresh the row instead of duplicating it.
5. **Food Memory** - `services/food_memory_service.py` (`record_event`), events
   `meal_viewed`, `recommendations_viewed`, `recommendation_selected`, with
   duplicate windows. Cart and order events are deliberately **not** added
   (Phase 6).
6. **Frontend** - `recommendations.html` + `js/recommendations.js` (cards,
   match %, "why it matches", empty / error / loading states, history table),
   customer navbar links, dashboard buttons, meal-view event on the dish page.
7. **Migration** - none needed (see `PROJECT_AUDIT.md`, Phase 5 update).
8. **Tests (written, not run)** - `tests/test_preferences.py`,
   `tests/test_recommendations.py`, `tests/test_food_memory.py`, plus the
   optional `tests/frontend/mock_phase5_check.js`.

## Files

### Created
```
backend/app/routes/preferences.py
backend/app/routes/recommendations.py
backend/app/routes/food_memory.py
backend/app/services/preference_service.py
backend/app/services/recommendation_service.py
backend/app/services/food_memory_service.py
frontend/preferences.html
frontend/recommendations.html
frontend/js/preferences.js
frontend/js/recommendations.js
tests/test_preferences.py
tests/test_recommendations.py
tests/test_food_memory.py
tests/frontend/mock_phase5_check.js
docs/RECOMMENDATIONS.md
docs/PHASE5_PROGRESS.md
```

### Modified
```
backend/app/__init__.py            (registers 3 blueprints)
backend/app/services/meal_service.py  (additive: visible_meal_rows, tastes, portion_sizes)
frontend/js/api.js                 (Phase 5 helpers appended)
frontend/js/layout.js              (customer nav links)
frontend/js/browse.js              (one call after the dish page renders)
frontend/dashboard.html            (customer buttons, updated notice)
frontend/css/style.css             (appended styles)
README.md
docs/PROJECT_AUDIT.md
```

No existing test file was edited. `requirements.txt`, `schema.sql` and the
migrations are unchanged.

## What was run (and what was not)

Run: Python and JavaScript syntax checks; HTML id/link checks; 41 isolated
checks of the pure scoring and validation functions (database layer stubbed);
the 16-check Phase 5 browser run against a stand-in API (with a deliberate
break to prove it can fail); the 13-check Phase 4 browser run again.

**Not run: pytest (any file), anything against MySQL, a real browser against
real Flask.** Details and the full table are in `docs/PROJECT_AUDIT.md`.

## Windows PowerShell instructions

1. Unzip `fooddna18_phase5.zip` over (or next to) your project folder,
   keeping your own `.env` and `venv\` (the ZIP contains neither).
   ```powershell
   cd C:\Users\Hello\Desktop
   Expand-Archive -Path .\fooddna18_phase5.zip -DestinationPath .\fooddna18_phase5 -Force
   ```
   Then copy your `.env` into `fooddna18_phase5\fooddna18\` (or copy the
   changed files into your existing folder).
2. No new packages and **no database migration** this phase. If your virtual
   environment is already set up you can skip installation:
   ```powershell
   cd C:\Users\Hello\Desktop\fooddna18
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Run against the development data (window 1):
   ```powershell
   cd backend
   python init_dev_database.py
   $env:DB_NAME = "fooddna_dev"
   python seed_demo_data.py
   python run.py
   ```
4. Frontend (window 2):
   ```powershell
   cd C:\Users\Hello\Desktop\fooddna18\frontend
   python -m http.server 5500
   ```
5. Open <http://127.0.0.1:5500/index.html>, register a customer, log in, then
   follow `README.md` section 5.1.
6. **Later, in the testing phase** (not now): `python -m pytest -q` from the
   project root.

## Known limitations and unverified behaviour

See `docs/PROJECT_AUDIT.md` (Phase 5 update) and `docs/RECOMMENDATIONS.md`
section 6. The main ones:

- Everything database-backed is unverified until pytest and the manual
  checklist have run on your machine.
- Matching is exact text; free-text labels from restaurants can disagree.
- Customers with a dietary preference do not see unlabelled dishes.
- Food Memory is recorded, not yet used for ranking.
- The Phase 5 role-refusal tests assume an approved `restaurant_admin` can log
  in without a restaurant link; if not, adjust the helper.

## Ready for Phase 6 (cart and ordering)

Not started, by design. Things Phase 6 will need, already noted in the audit:

- Decide the open questions in `PROJECT_AUDIT.md` section F: one restaurant per
  cart, where payment status lives, offers at checkout.
- Migration `003`: unique `(cart_id, meal_id)` on `cart_items`.
- Register `added_to_cart` and `order_placed` in
  `food_memory_service.EVENT_TYPES` and call `record_event(...)`.
- Reuse `meal_service.get_meal` / the visibility rule so hidden or sold-out
  meals cannot be added or ordered.
