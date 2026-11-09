-- Migration 006: Add idempotency_key to orders (fix 1.3)
-- Idempotent: checks information_schema before altering.

SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND COLUMN_NAME = 'idempotency_key'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(64) NULL AFTER discount_amount',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add unique index per user+key if not present
SET @idx_exists = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND INDEX_NAME = 'uq_orders_user_idempotency'
);

SET @sql2 = IF(@idx_exists = 0,
    'ALTER TABLE orders ADD UNIQUE INDEX uq_orders_user_idempotency (user_id, idempotency_key)',
    'SELECT 1'
);
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
