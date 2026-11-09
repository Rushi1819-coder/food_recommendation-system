# FoodDNA — Phase 6 Progress Report

Phase 6: Shopping Cart, Checkout and Food Ordering.

**Status: implemented. NOT tested against Flask and MySQL.** Testing is
deferred to the dedicated testing phase, as agreed. Nothing here has passed
`python -m pytest -q`.

---

## What was built

### 1. Database migration 003

`database/migrations/003_cart_items_unique.sql` — enforces `UNIQUE (cart_id,
meal_id)` on `cart_items` so that adding the same dish twice increments the
existing row's quantity instead of creating a duplicate row.

The migration file includes a documented **pre-inspection query** and a
**safe data-preserving consolidation procedure** for anyone applying it to an
existing database that might already contain duplicate rows. No records are
deleted or merged silently.

### 2. Backend services

#### `backend/app/services/cart_service.py`
- `get_or_create_cart(user_id)` — retrieves or lazily creates the customer's
  active cart; handles the unique-constraint race via rollback + re-query.
- `serialize_cart(cart)` — produces a complete JSON-ready dict with line
  totals, subtotal, delivery fee and grand total using `Decimal` arithmetic.
- `add_to_cart(user_id, meal_id, quantity)` — validates meal, category and
  restaurant status; enforces single-restaurant-per-cart (raises
  `CartRestaurantConflictError`); increments quantity on duplicate entries;
  records `added_to_cart` Food Memory event.
- `update_cart_item_quantity(user_id, item_id, quantity)` — re-validates
  availability before accepting the update.
- `remove_cart_item(user_id, item_id)` — removes one item; cart row is
  preserved.
- `clear_cart(user_id)` — deletes all `CartItem` rows while keeping the
  parent `Cart` row.
- Quantity bounds: minimum 1, maximum 50 per dish. Delivery fee is read from
  `DEFAULT_DELIVERY_FEE` in app config (default `40.00`).

#### `backend/app/services/order_service.py`
- `place_order(user_id, delivery_address, payment_method)` — fully
  transactional checkout:
  1. Validates delivery address (10–500 characters) and payment method.
  2. Re-fetches every cart item from MySQL (fresh state check).
  3. Revalidates each meal's `is_available`, category `is_active` and
     restaurant `status = 'approved'`.
  4. Recalculates every unit price, line total, subtotal, delivery fee and
     grand total server-side using `Decimal` — client-supplied prices are
     silently ignored.
  5. Creates `Order`, `OrderItem` rows, initial `OrderStatusHistory` record
     (`status = 'pending'`), `Payment` record (`cash_on_delivery`, `pending`)
     and a Food Memory `order_placed` event, all in one `db.session.commit()`.
  6. Clears `CartItem` rows inside the same transaction.
  7. On any exception, performs a full `db.session.rollback()` — no partial
     orders, orphaned payments or unlinked Food Memory events can persist.
- `list_customer_orders(user_id, page, page_size)` — paginated order history,
  newest-first.
- `get_order_details(user_id, order_id)` — full detail view (items, status
  history, payment); returns `None` if the order belongs to a different user.
- `get_order_status(user_id, order_id)` — status and history only.

### 3. Backend routes

#### `backend/app/routes/cart.py`  (`/api/cart`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cart` | Retrieve current cart (creates one if none exists) |
| POST | `/api/cart/items` | Add meal; returns 409 + `RESTAURANT_CONFLICT` code on multi-restaurant conflict |
| PATCH | `/api/cart/items/<id>` | Update quantity |
| DELETE | `/api/cart/items/<id>` | Remove one item |
| DELETE | `/api/cart` | Clear all items |

All write routes require an `X-CSRF-Token` header and `customer` role.

#### `backend/app/routes/orders.py`  (`/api/orders`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/orders` | Checkout and place order |
| GET | `/api/orders` | Paginated order history |
| GET | `/api/orders/<id>` | Full order details |
| GET | `/api/orders/<id>/status` | Current status and history |

All routes require the `customer` role. Write routes require CSRF.

Both blueprints were registered in `backend/app/__init__.py`.

### 4. Frontend pages and JavaScript

#### Pages (HTML shells)
- `frontend/cart.html` — shopping cart page
- `frontend/checkout.html` — delivery address + payment + order confirmation
- `frontend/orders.html` — order history list
- `frontend/order-details.html` — full order detail and status timeline

All four pages load `js/api.js`, `js/layout.js` and their own JS module.

#### JavaScript modules
- **`frontend/js/cart.js`** — renders empty state, active cart table with
  quantity +/− controls, line totals, bill summary card with subtotal /
  delivery fee / total, "Clear Cart" and "Proceed to Checkout" actions.
- **`frontend/js/checkout.js`** — loads cart contents server-side; shows
  order summary; delivery address textarea with live character counter;
  Cash on Delivery radio (pre-selected); client-side length guard (≥10 chars);
  `confirm()` dialog before sending; on success redirects to order-details
  with `?placed=1`.
- **`frontend/js/orders.js`** — paginated order card list with status badge,
  item summary, restaurant name, total and "View Order Details →" link.
- **`frontend/js/order-details.js`** — success banner on first arrival
  (`?placed=1`); order header with status badge; dishes table; status
  timeline; delivery address card; payment and charges card; "Order More"
  and "Back to Orders" action buttons.

#### Shared API helpers added to `frontend/js/api.js` (Phase 6 section)
`fetchCart`, `addToCart`, `updateCartItem`, `removeCartItem`, `clearCart`,
`placeOrder`, `fetchOrders`, `fetchOrderDetails`, `fetchOrderStatus`,
`showToast`, `handleAddToCart` (shared add-to-cart with restaurant-conflict
prompt and retry).

#### Navigation (`frontend/js/layout.js`)
- Authenticated customers see **Cart** and **My Orders** links in the navbar.
- `sections` map keeps "Cart" active on `checkout.html` and "My Orders" active
  on `order-details.html`.

### 5. Food Memory integration

- `added_to_cart` event is recorded inside `cart_service.add_to_cart()`.
- `order_placed` event is recorded inside `order_service.place_order()`,
  joined to the same transaction so it rolls back if the order fails.
- Both events use `food_memory_service.record_event(commit=False)` to avoid
  premature intermediate commits.

### 6. Payment model

Cash on Delivery only. No real card transactions are fabricated. A `Payment`
row is created with `payment_method = 'cash_on_delivery'` and
`payment_status = 'pending'`; `transaction_id` is `NULL`. The pending status
persists until a future phase (delivery staff marks payment received).

---

## Files created

```
backend/app/routes/cart.py
backend/app/routes/orders.py
backend/app/services/cart_service.py
backend/app/services/order_service.py
frontend/cart.html
frontend/checkout.html
frontend/orders.html
frontend/order-details.html
frontend/js/cart.js
frontend/js/checkout.js
frontend/js/orders.js
frontend/js/order-details.js
database/migrations/003_cart_items_unique.sql
tests/test_cart.py
tests/test_orders.py
docs/PHASE6_PROGRESS.md
```

## Files modified

```
backend/app/__init__.py    (registers cart_bp and orders_bp)
frontend/js/api.js         (Phase 6 helpers appended)
frontend/js/layout.js      (Cart and My Orders nav links; sections map)
README.md                  (Phase 6 setup, API table, status update)
docs/PROJECT_AUDIT.md      (completion table updated)
```

---

## Design decisions

| Decision | Rationale |
|---|---|
| One restaurant per cart | Matches `orders.restaurant_id` (non-nullable); avoids splitting an order across kitchens |
| Server-side Decimal pricing | Client-supplied prices are ignored; re-read from DB at checkout |
| Cart row preserved on clear | Avoids race condition if two tabs both try to create a new cart |
| Atomic checkout transaction | `flush()` for `order.id`, then all inserts + cart clear + Food Memory in one `commit()` |
| No mock payment | Fabricating a transaction ID would misrepresent the system; COD pending is honest |
| Delivery fee from config | `DEFAULT_DELIVERY_FEE` (default ₹40.00); no per-restaurant variability yet |
| 409 with `RESTAURANT_CONFLICT` code | Lets the frontend show a clear prompt to clear and retry |

---

## What was run (and what was not)

- Python and JavaScript syntax checks.
- HTML id and link checks.
- Static review of Decimal arithmetic in service files.
- Manual trace of the checkout transaction path.

**Not run: pytest (any file), anything against MySQL, a real browser against
real Flask.** Testing is deferred to the dedicated testing phase (Phase 11).
See `docs/PROJECT_AUDIT.md` for the full verification status.

---

## Test files written (not yet executed)

| File | Tests |
|---|---|
| `tests/test_cart.py` | 12 tests covering empty state, add item, quantity increment, unique-constraint enforcement, restaurant conflict (409), unavailable/unapproved meals, invalid quantities, update, remove, clear, cross-user isolation, Food Memory event |
| `tests/test_orders.py` | 10 tests covering empty-cart rejection, address validation, successful checkout with server-side pricing, DB record creation, cart cleared after checkout, duplicate-submit safety, transaction rollback, order history pagination, order details, cross-customer isolation, Food Memory event |

---

## Known limitations and unverified behaviour

- All database-backed behaviour is unverified until pytest and the manual
  checklist have run on the real MySQL instance.
- Delivery fee is a flat ₹40.00; no per-restaurant or distance-based logic.
- No order cancellation endpoint (future phase).
- No real-time status updates; status remains `pending` until manually changed.
- Food Memory `order_placed` stores `meal_id = None` (the event is per order,
  not per dish); individual meal events use `added_to_cart`.
- The status-history timeline uses `created_at` from `TimestampMixin`; this
  is set server-side, not adjustable.

---

## Ready for Phase 7 (Customer Dashboard)

The dashboard will be able to read order history and cart counts from the
Phase 6 APIs already in place:
- `GET /api/orders?page=1&page_size=5` for recent orders widget.
- `GET /api/cart` for the cart item-count badge.


---

## Subsequent implementation note (12 Oct 2026)

The working archive was extended with Phase 7–10 code after this Phase 6 report was created. See `docs/PHASE7_10_PROGRESS.md` and `docs/PROJECT_AUDIT.md`; these later workflows are coded but not yet verified against MySQL.


## Validation policy update — 16 October 2026

The account validation policy was updated after the original phase work: new account names allow Unicode letters and spaces only, and new account email addresses must use exactly `@gmail.com`. The customer registration, Restaurant Admin applicant and Super Admin-created operator flows now use matching frontend/backend rules. Existing users are not blocked from login solely because an older stored email is not Gmail. The user reported the full test suite passed before this update; rerun the suite now because the validation code and some test fixtures have changed. Full real-browser workflow validation remains pending.
