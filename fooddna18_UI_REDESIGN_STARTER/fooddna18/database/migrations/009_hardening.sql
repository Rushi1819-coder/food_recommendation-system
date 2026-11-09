-- Migration 009: DB hardening - indexes and CHECK constraints (fix 1.15)
-- All idempotent via information_schema checks.
-- Run AFTER migrations 001-008.
-- Does NOT alter data; reports violations in CHECK section.

-- ============================================================
-- SECTION 1: Performance indexes
-- ============================================================

-- food_memory(user_id, event_type, created_at)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='food_memory' AND INDEX_NAME='idx_memory_user_type_time');
SET @sql = IF(@idx=0, 'ALTER TABLE food_memory ADD INDEX idx_memory_user_type_time (user_id, event_type, created_at)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- notifications(user_id, is_read, created_at)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='notifications' AND INDEX_NAME='idx_notifications_user_read_time');
SET @sql = IF(@idx=0, 'ALTER TABLE notifications ADD INDEX idx_notifications_user_read_time (user_id, is_read, created_at)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- orders(user_id, placed_at)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND INDEX_NAME='idx_orders_user_placed');
SET @sql = IF(@idx=0, 'ALTER TABLE orders ADD INDEX idx_orders_user_placed (user_id, placed_at)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- orders(restaurant_id, order_status)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND INDEX_NAME='idx_orders_restaurant_status');
SET @sql = IF(@idx=0, 'ALTER TABLE orders ADD INDEX idx_orders_restaurant_status (restaurant_id, order_status)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- meals(restaurant_id, is_available)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='meals' AND INDEX_NAME='idx_meals_restaurant_available');
SET @sql = IF(@idx=0, 'ALTER TABLE meals ADD INDEX idx_meals_restaurant_available (restaurant_id, is_available)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- feedback(food_id)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='feedback' AND INDEX_NAME='idx_feedback_food');
SET @sql = IF(@idx=0, 'ALTER TABLE feedback ADD INDEX idx_feedback_food (food_id)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- feedback(restaurant_id)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='feedback' AND INDEX_NAME='idx_feedback_restaurant');
SET @sql = IF(@idx=0, 'ALTER TABLE feedback ADD INDEX idx_feedback_restaurant (restaurant_id)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- recommendations(user_id, generated_at)
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='recommendations' AND INDEX_NAME='idx_recommendations_user_time');
SET @sql = IF(@idx=0, 'ALTER TABLE recommendations ADD INDEX idx_recommendations_user_time (user_id, generated_at)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- SECTION 2: CHECK constraint helpers
-- Violation reports: SELECT violating rows BEFORE adding checks.
-- These SELECTs never fail; they just surface bad data.
-- ============================================================

-- Report cart_items with quantity out of range (do not block)
SELECT 'VIOLATION: cart_items.quantity' AS check_name, id, quantity
FROM cart_items WHERE quantity < 1 OR quantity > 50;

-- Report order_items with quantity < 1
SELECT 'VIOLATION: order_items.quantity' AS check_name, id, quantity
FROM order_items WHERE quantity < 1;

-- Report meals with price < 0
SELECT 'VIOLATION: meals.price' AS check_name, id, name, price
FROM meals WHERE price < 0;

-- Report orders with total_amount < 0
SELECT 'VIOLATION: orders.total_amount' AS check_name, id, total_amount
FROM orders WHERE total_amount < 0;

-- Report offers with discount out of range
SELECT 'VIOLATION: offers.discount_percent' AS check_name, id, discount_percent
FROM offers WHERE discount_percent <= 0 OR discount_percent > 100;

-- Report offers with end_date < start_date
SELECT 'VIOLATION: offers.date_order' AS check_name, id, start_date, end_date
FROM offers WHERE end_date < start_date;

-- ============================================================
-- SECTION 3: Add CHECK constraints (MySQL 8.0.16+ / MariaDB 10.2+)
-- Each is idempotent via information_schema.TABLE_CONSTRAINTS.
-- ============================================================

-- cart_items.quantity BETWEEN 1 AND 50
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='cart_items' AND CONSTRAINT_NAME='chk_cart_item_quantity');
SET @sql = IF(@chk=0, 'ALTER TABLE cart_items ADD CONSTRAINT chk_cart_item_quantity CHECK (quantity BETWEEN 1 AND 50)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- order_items.quantity >= 1
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND CONSTRAINT_NAME='chk_order_item_quantity');
SET @sql = IF(@chk=0, 'ALTER TABLE order_items ADD CONSTRAINT chk_order_item_quantity CHECK (quantity >= 1)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- meals.price >= 0
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='meals' AND CONSTRAINT_NAME='chk_meal_price');
SET @sql = IF(@chk=0, 'ALTER TABLE meals ADD CONSTRAINT chk_meal_price CHECK (price >= 0)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- orders.total_amount >= 0
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND CONSTRAINT_NAME='chk_order_total');
SET @sql = IF(@chk=0, 'ALTER TABLE orders ADD CONSTRAINT chk_order_total CHECK (total_amount >= 0)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- offers.discount_percent > 0 AND <= 100
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='offers' AND CONSTRAINT_NAME='chk_offer_discount');
SET @sql = IF(@chk=0, 'ALTER TABLE offers ADD CONSTRAINT chk_offer_discount CHECK (discount_percent > 0 AND discount_percent <= 100)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- offers.end_date >= start_date
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='offers' AND CONSTRAINT_NAME='chk_offer_dates');
SET @sql = IF(@chk=0, 'ALTER TABLE offers ADD CONSTRAINT chk_offer_dates CHECK (end_date >= start_date)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- orders.order_status enum check
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND CONSTRAINT_NAME='chk_order_status');
SET @sql = IF(@chk=0,
    "ALTER TABLE orders ADD CONSTRAINT chk_order_status CHECK (order_status IN ('pending','confirmed','preparing','ready_for_pickup','picked_up','out_for_delivery','delivered','cancelled'))",
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- payments.payment_status enum check
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments' AND CONSTRAINT_NAME='chk_payment_status');
SET @sql = IF(@chk=0,
    "ALTER TABLE payments ADD CONSTRAINT chk_payment_status CHECK (payment_status IN ('pending','paid','cancelled','not_applicable'))",
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- users.account_status enum check
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' AND CONSTRAINT_NAME='chk_user_account_status');
SET @sql = IF(@chk=0,
    "ALTER TABLE users ADD CONSTRAINT chk_user_account_status CHECK (account_status IN ('active','pending','rejected','suspended'))",
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- restaurants.status enum check
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='restaurants' AND CONSTRAINT_NAME='chk_restaurant_status');
SET @sql = IF(@chk=0,
    "ALTER TABLE restaurants ADD CONSTRAINT chk_restaurant_status CHECK (status IN ('pending','approved','rejected','suspended'))",
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- admin_approvals.status enum check
SET @chk = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='admin_approvals' AND CONSTRAINT_NAME='chk_approval_status');
SET @sql = IF(@chk=0,
    "ALTER TABLE admin_approvals ADD CONSTRAINT chk_approval_status CHECK (status IN ('pending','approved','rejected'))",
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;
