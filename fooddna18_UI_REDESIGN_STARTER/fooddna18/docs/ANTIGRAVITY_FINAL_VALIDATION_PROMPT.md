# FoodDNA — Complete Project Audit, Fixes, Validation and Final Packaging Prompt

You are continuing an **existing FoodDNA project**. Do not rebuild it from scratch. Use the current project files and the documentation in `README.md`, `docs/PROJECT_AUDIT.md`, `docs/PHASE5_PROGRESS.md`, `docs/PHASE6_PROGRESS.md`, `docs/PHASE7_10_PROGRESS.md`, `docs/PHASE11_TEST_PLAN.md`, and `docs/FINAL_PACKAGE_CHECKLIST.md` as the starting source of truth. Inspect the real code before changing anything.

## 1. Main objective

Bring the existing FoodDNA project through Phases 1–10 into a consistent, working state, finish Phase 11 validation, fix defects exposed by that validation, and prepare one clean final project ZIP. Work quickly but do not skip verification or claim a feature works merely because a file exists.

**Stack:** Python Flask backend, SQLAlchemy/PyMySQL, MySQL, REST JSON APIs, HTML/CSS/JavaScript and Bootstrap frontend. Preserve the current application architecture, route blueprints, file structure, and working behavior.

## 2. Required account validation rules

Implement the same rules in the UI and server. The backend is authoritative; direct API requests must not bypass validation.

### Full name

- Accept Unicode letters and ordinary spaces only.
- Reject digits, punctuation, hyphens, apostrophes, periods, emoji, control characters and other symbols.
- In account-creation forms, remove disallowed characters as the user types or pastes text. Still validate on submission and on the backend.
- Apply this consistently to customer registration, Restaurant Admin applicant account name, Super Admin-created staff/delivery partner account names, and the command-line Super Admin creation workflow.
- Expected examples: `Rushi Sharma`, `José García`, and `राहुल शर्मा` are accepted. `Asha 123`, `Rushi-Sharma`, `O'Brien`, `A. Kumar`, and `Name 😀` are rejected/cleaned in the UI and rejected by the API if directly submitted.

### New-account email

- New account email addresses must use the exact `@gmail.com` domain, case-insensitively.
- Reject Yahoo, Outlook, arbitrary domains, `@gmail.co`, `@googlemail.com`, malformed addresses, double dots, and lookalikes such as `rushi@gmail.com.evil`.
- Enforce this in customer registration, Restaurant Admin application login email, Super Admin-created staff/delivery accounts, and CLI Super Admin creation. Keep frontend and backend messages consistent.
- Examples: `rushi@gmail.com`, `first.last+tag@gmail.com`, and `RUSHI@GMAIL.COM` are syntactically accepted. `rushi@yahoo.com`, `rushi@gmail.co`, and `rushi@gmail.com.evil` are rejected.
- Apply the Gmail-only restriction to **new account creation**. Do not accidentally lock existing users out of login or password-reset requests solely because an older stored address uses a different domain. The optional restaurant contact email is a separate business-contact field; keep a normal email syntax check there unless the project owner explicitly changes that requirement.
- A syntactically valid Gmail address is not proof that the mailbox exists. Do not claim real mailbox verification unless an email-verification flow is actually implemented.

### Passwords and API validation

- Preserve strong password checks, confirmation matching, rate limiting, CSRF, session checks and role-based permissions.
- Ensure newly created staff/delivery accounts have a consistent strong-password rule, including the existing minimum length requirement for those accounts.
- Never log or return plaintext passwords, password hashes, reset tokens or secrets.
- Never weaken or remove tests just to make the suite pass; fix production code and the underlying assumptions instead.

## 3. Phase-by-phase behavior to inspect and validate

Compare the implementation to the current project docs and verify these features without inventing payment/email services that are not implemented.

### Foundation and authentication (Phases 1–3)

- Flask application factory and all blueprints register correctly.
- `/api/health` and `/api/health/db` work.
- Registration, login, logout, sessions, CSRF, role checks, throttling/lockout, password reset token expiry/one-use behavior, suspended/rejected/pending account handling, and Restaurant Admin application/status checking work.
- Customers cannot elevate their role by sending a `role` field. Users cannot read or mutate another user's private records.

### Browsing (Phase 4)

- Public pages/APIs hide unavailable meals, inactive categories, and unapproved restaurants.
- Restaurant and meal searches, category/cuisine/type/dietary filters, price bounds, sorting, pagination, URL parameters, empty states and malformed IDs behave correctly.
- Server-provided strings are inserted safely as text, and user search input cannot inject SQL or HTML.

### Preferences, recommendations and Food Memory (Phase 5)

- Save/update preferences, validate budgets, return a stable and explained ranking, apply diet/budget hard filters, and prevent customer data leakage.
- Verify Food Memory events and history are attributed to the signed-in user and contain no credentials.
- Audit the documented gap: recommendation ranking currently may not use every Food Memory/feedback signal. If the roadmap requires these signals now, implement a small explainable scoring adjustment with tests; otherwise document it accurately as a future enhancement rather than claim it is already used.

### Cart, checkout and ordering (Phase 6)

- A cart contains one restaurant only; a conflicting restaurant add returns a useful 409 response.
- The server uses database prices and `Decimal` arithmetic, and ignores client-supplied totals/prices.
- COD (`cash_on_delivery`) is the only supported payment method unless the project requirements explicitly change. Do not fabricate online payment gateway transactions.
- Checkout validates delivery address and rechecks meal/category/restaurant availability. Order, order items, status history, payment row, Food Memory event, and cart clearing must be atomic; rollback must leave no partial records.
- CartItem uniqueness migration 003 must not silently delete or merge records. Check duplicate `(cart_id, meal_id)` rows before applying it and stop/report if unsafe duplicates exist.

### Dashboard and operations (Phases 7–10)

- Customer dashboard counts and recent orders are scoped to the current user.
- Super Admin can review/approve/reject applications and manage permitted accounts. Prevent self-suspension or privilege escalation.
- Restaurant Admin can manage only their linked restaurant's meals/orders/offers.
- Staff can operate only on orders for their assigned restaurant.
- Delivery partners can claim valid orders safely, cannot both claim the same order, can perform only allowed status transitions, and COD payment is marked received only at the correct delivery completion step.
- Offers must be active, in date range, and belong to the restaurant in the cart; discounts/totals are recalculated server-side.
- Feedback is limited to eligible delivered-order meals; notifications and Food Memory timelines are user-scoped.

## 4. Find and fix mismatches

- Inspect `backend/app/__init__.py` and preserve its complete `create_app()` registration and all existing blueprints. Never replace the entire app factory blindly.
- Verify frontend routes and calls match Flask API endpoints and expected JSON shapes.
- Update every stale test fixture, mock-browser expectation, helper text, validation error message, README instruction and audit/progress report when a policy changes.
- Pay special attention to old assumptions in `tests/test_auth.py`, `tests/test_validation.py`, `tests/test_operations.py`, and `tests/frontend/mock_browser_check.js` that may still expect non-Gmail domains or punctuation in account names.
- Check that all new-account entry paths use the same account validation helpers, including `backend/create_super_admin.py`.
- Review the existing health endpoints rather than adding duplicate/conflicting routes.
- Fix real defects; do not silence exceptions, skip relevant tests, or change assertions to mask bugs.

## 5. Safe database and secret handling — mandatory

- Preserve the real `fooddna` database and its existing data. Do not drop, reset, truncate, overwrite, seed, or migrate the real database automatically.
- Never read secrets into the report, paste them into logs, or include `.env` in any ZIP. Do not overwrite the user's `.env` file.
- The pytest fixture drops and rebuilds the database named by `TEST_DB_NAME`. Before executing tests, verify it ends in `_test`, differs from `DB_NAME`, and contains no data the user needs. Prefer a clearly dedicated test DB such as `fooddna_phase11_test` only after checking it is safe to recreate.
- Migration 004 must be inspected for already-present columns/constraints before use. Back up the intended database before any manual migration. Never run migrations automatically against the real database during code review.
- Do not include `venv`, `.venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.pyc`, `.env`, credentials, or editor/OS temporary files in the deliverable.
- The previously uploaded project archive contained a real `.env`; if its secrets were real, advise rotating the MySQL password and Flask secret key.

## 6. Verification steps

Run what is available and report exact results:

1. Python syntax/compilation for all backend and test `.py` files.
2. JavaScript syntax checks for all frontend scripts and test scripts.
3. HTML local `href`/`src` existence checks and duplicate-ID checks.
4. Standalone validation cases for accepted and rejected names/emails.
5. Confirm app imports and all intended blueprints/routes register if the dependencies are installed.
6. Run `python -m pytest -q` against the dedicated disposable `_test` database only after confirming it is safe to recreate. Save the full output and fix failures.
7. If the optional Playwright dependency is installed, run the frontend mock checks sequentially. Do not say they passed if they were not run.
8. On the user's Windows/MySQL machine, manually test backend/database health, frontend loading, registration, login/logout, browsing, preferences/recommendations, cart, COD checkout, order details, admin approvals, restaurant operations, delivery workflow, offers, feedback and notifications.
9. Verify migrations against a disposable test database; do not execute destructive steps against the real database.

Record each check as **PASS**, **FAIL**, **BLOCKED**, or **NOT RUN**, with a brief explanation. Distinguish syntax tests from database integration tests and real browser validation.

## 7. Documentation and final deliverable

- Update `README.md`, `docs/PROJECT_AUDIT.md`, `docs/PHASE11_TEST_PLAN.md`, and any relevant phase progress report to match the actual code and verification status.
- Keep current limitations truthful: COD only; no real email sending unless implemented; recommendations should not be described as feedback/Food Memory-driven unless code really uses those signals.
- Create `fooddna18_FINAL.zip` from the complete current project, with all needed source, migrations, tests and documentation, but without secrets, virtual environments, caches or local backups.
- Inspect the ZIP after creation; verify expected key files exist and sensitive items are absent.
- At the end, provide: a concise list of changed files, actual checks run, full pytest result if run, manual checks still pending, known limitations, and the verified path to the final ZIP.

**Do not stop after writing a plan. Inspect the repository, make the needed changes, run the checks that are available, fix every reproducible error, and then package the project. Do not start a new phase or redesign the application unless the existing project documentation requires it.**
