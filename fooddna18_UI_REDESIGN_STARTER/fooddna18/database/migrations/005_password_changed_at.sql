-- Migration 005: Add password_changed_at to users (fix 1.8)
-- Idempotent: checks information_schema before altering.

SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'password_changed_at'
);

-- Only add if missing
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE users ADD COLUMN password_changed_at DATETIME NULL AFTER last_login_at',
    'SELECT 1'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
