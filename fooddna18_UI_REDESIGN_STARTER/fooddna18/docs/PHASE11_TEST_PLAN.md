# Phase 11 — End-to-End Test and Database Consistency Plan

**Current state:** test files are present, but this test pass has not been executed against a live MySQL instance.

## Safe test sequence (Windows PowerShell)

1. Back up the working project folder and database. Do not experiment on the only copy.
2. Confirm `.env` points to the intended real database and remember that the pytest fixture uses `fooddna_test`, a separate test database that it drops and recreates. Never set `TEST_DB_NAME` to `fooddna` or `fooddna_dev`.
3. Inspect/apply database migrations in order. Migration 003 requires checking for duplicate `(cart_id, meal_id)` pairs. Migration 004 should be applied once after checking for existing columns and taking a backup.
4. Activate the project virtual environment and install `requirements.txt`.
5. Ensure MySQL is running and the configured user is allowed to create/drop the isolated `fooddna_test` database.
6. Run `python -m pytest -q` from the project root. Save the complete output, not only the pass count.
7. Start Flask and the static frontend and run the manual checklist below.

## Test modules

- `tests/test_foundation.py`, `test_auth.py`, `test_rbac_and_cors.py`: startup/authentication/security basics.
- `tests/test_validation.py`, `test_browsing.py`, `test_seed.py`: inputs, browse APIs, dev seed isolation.
- `tests/test_preferences.py`, `test_recommendations.py`, `test_food_memory.py`: preference/recommendation history.
- `tests/test_cart.py`, `test_orders.py`: cart/checkout integrity and customer order isolation.
- `tests/test_operations.py`: dashboard permissions and Super Admin approval flow.
- `tests/test_engagement.py`: offer visibility and notification isolation.

## Registration validation cases

For customer registration, Restaurant Admin applications, and Super Admin-created staff/delivery accounts, verify these cases at both the UI and API layers:

- Accepted names: `Rushi Sharma`, `José García`, `राहुल शर्मा`.
- Rejected names: `Asha 123`, `Rushi-Sharma`, `O'Brien`, `A. Kumar`, emoji and control characters. The UI should strip unsupported characters as the user types/pastes; the backend must reject any invalid value sent directly.
- Accepted new account emails: `rushi@gmail.com`, `first.last+tag@gmail.com`.
- Rejected new account emails: `rushi@yahoo.com`, `rushi@gmail.co`, `rushi@gmail.com.evil`, `a..b@gmail.com`, and malformed addresses.
- Check case normalization (`RUSHI@GMAIL.COM` is stored as `rushi@gmail.com`) and duplicate-account rejection.
- Do not apply the Gmail-only account-creation rule to login or password-reset lookups for already-existing accounts. The optional restaurant contact email is not the account/login email.
- Confirm weak passwords and mismatched confirmation are rejected; never log a plaintext password.

## Manual workflow checklist

- Register a customer using valid and invalid name/email inputs above, then sign in/out; verify CSRF-protected changes fail without a token.
- Verify browsing hides unavailable meals, inactive categories, and unapproved restaurants.
- Save preferences, view recommendations, and check Food Memory timeline.
- Add meals from one restaurant; verify a second restaurant is rejected until the cart is cleared.
- Checkout without an offer and with a valid offer; compare server order subtotal, discount, delivery fee and total. Verify client edits cannot change prices.
- Review an application using a Super Admin account. Confirm the approved restaurant becomes public and rejected accounts remain blocked.
- Create staff and delivery partner accounts with a Gmail account address, letters/spaces-only name, and strong password; advance an order through kitchen and delivery statuses. Verify two partners cannot claim the same order.
- Deliver a COD order and verify payment status becomes paid only at delivery completion.
- Submit feedback for a delivered order; verify feedback for pending orders and meals not in the order is rejected.
- Mark notifications read; verify one user cannot access another user's notifications, feedback or orders.

## Evidence to record

Record the exact Python/MySQL versions, complete pytest output, migration results, and manual checklist results. A syntax pass does not establish working database behaviour. If any test fails, preserve the failing database/test output and fix the cause rather than weakening the assertion.
