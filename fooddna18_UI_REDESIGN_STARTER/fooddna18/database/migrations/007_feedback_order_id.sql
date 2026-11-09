-- Migration 007: Add order_id to feedback + unique constraint (fix 1.13)
-- Idempotent: checks information_schema before altering.

-- Add order_id column if missing
SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'feedback'
      AND COLUMN_NAME = 'order_id'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE feedback ADD COLUMN order_id BIGINT NULL AFTER customer_id, ADD CONSTRAINT fk_feedback_order FOREIGN KEY (order_id) REFERENCES orders(id)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add unique constraint if missing (one review per meal per order)
SET @idx_exists = (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'feedback'
      AND CONSTRAINT_NAME = 'uq_feedback_customer_order_food'
);

SET @sql2 = IF(@idx_exists = 0,
    'ALTER TABLE feedback ADD CONSTRAINT uq_feedback_customer_order_food UNIQUE (customer_id, order_id, food_id)',
    'SELECT 1'
);
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
