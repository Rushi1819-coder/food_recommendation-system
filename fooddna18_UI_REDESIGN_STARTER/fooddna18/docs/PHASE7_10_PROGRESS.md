# FoodDNA — Phases 7–10 Progress Report

**Date:** 12 October 2026  
**Implementation status:** Code added; static syntax checks run; Flask/MySQL integration testing not yet performed.

## Phase 7 — Customer dashboard

- Added `GET /api/dashboard/customer` for order counts, active order count, cart quantity, recommendation history count, and recent orders.
- Updated `frontend/dashboard.html` with an operations panel and added `frontend/js/dashboard.js` for a role-aware view.
- Customer dashboard links to browsing and order history.

## Phase 8 — Super Admin and Restaurant Admin

- Super Admin can list pending/all approvals and approve or reject Restaurant Admin applications. Review actions set application/user/restaurant states, write a notification, and log an activity.
- Added Super Admin user list, restaurant list, account activation/suspension endpoint, and operator account creation for `staff` and `delivery_partner` roles.
- Restaurant Admin can view their restaurant's order/menu summary, list orders, advance allowable kitchen statuses, list meals, add meals and update meal fields.
- Added `frontend/restaurant-management.html` and `frontend/js/restaurant-management.js` for menu creation and availability controls.

## Phase 9 — Staff and delivery

- Staff can see orders for their linked restaurant and advance the preparation workflow.
- Delivery partners can see unassigned ready orders, claim one order under a row lock, advance delivery statuses, and mark COD payment received when an order is delivered.
- Added optional `orders.delivery_partner_id`; see migration `database/migrations/004_operations_engagement.sql`.

## Phase 10 — Feedback, offers, notifications and Food Memory

- Public current offers endpoint and Restaurant Admin create/update offer endpoints are implemented.
- Checkout can submit an optional offer ID; the backend checks that the offer is active, in date range, and belongs to the restaurant in the cart, then recalculates discount and total server-side.
- Feedback can be submitted only for a meal belonging to the signed-in customer's delivered order. Repeat feedback for the same customer/meal/restaurant is rejected.
- Added per-user notifications list, mark-one-read and mark-all-read endpoints and frontend pages.
- Food Memory event registry now supports order status changes and feedback events; added a customer timeline endpoint.

## Additions

- `backend/app/routes/operations.py`
- `backend/app/routes/engagement.py`
- `frontend/js/dashboard.js`
- `frontend/restaurant-management.html`
- `frontend/js/restaurant-management.js`
- `frontend/offers.html`, `frontend/notifications.html`, `frontend/feedback.html`
- `frontend/js/engagement.js`
- `database/migrations/004_operations_engagement.sql`
- `tests/test_operations.py`, `tests/test_engagement.py`

## Database migration note

Migration 004 adds nullable delivery partner and offer references, plus a `discount_amount` column to `orders`. It is additive and does not delete existing data. Back up the target database and inspect existing columns before applying. Do not apply it twice by hand.

## What was verified in this environment

- Python compilation (`compileall`) passed for backend and tests.
- Node JavaScript syntax checks passed for frontend JS and frontend test scripts.
- No runtime import check, pytest execution, MySQL migration, database-backed API test, or live-browser check was completed. This environment does not have Flask, Flask-SQLAlchemy, Flask-Cors, PyMySQL or a MySQL server installed.
- Treat these phases as **implemented but unverified** until the complete test suite and browser checklist are run in the configured local environment.

## Known limitations / follow-up for Phase 11

- Phase 7–10 endpoints have not been executed against MySQL; role/session/database interactions may still reveal integration issues.
- The delivery claim row lock must be confirmed on the target MySQL engine.
- Offer totals must be verified through actual checkout, especially rounding and expired/restaurant-mismatched offer rejection.
- The feedback form asks the customer for order and meal IDs; a future UI improvement can populate these from delivered order details.
- Real email delivery, card payment and live/push notifications are not implemented. COD is the only payment method.


## Validation policy update — 16 October 2026

The account validation policy was updated after the original phase work: new account names allow Unicode letters and spaces only, and new account email addresses must use exactly `@gmail.com`. The customer registration, Restaurant Admin applicant and Super Admin-created operator flows now use matching frontend/backend rules. Existing users are not blocked from login solely because an older stored email is not Gmail. The user reported the full test suite passed before this update; rerun the suite now because the validation code and some test fixtures have changed. Full real-browser workflow validation remains pending.
