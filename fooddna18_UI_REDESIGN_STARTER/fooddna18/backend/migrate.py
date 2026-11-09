"""
FoodDNA — Database migration runner (fix for issue 1.15).

Usage:
    python backend/migrate.py --database fooddna_dev
    python backend/migrate.py --database fooddna_dev --migrations-dir database/migrations

Behaviour:
- Creates a `schema_migrations` table if it does not exist.
- Applies migration files (*.sql) in lexicographic (numbered) order.
- Skips files already recorded in schema_migrations (idempotent).
- Never targets the real production database; refuses to run against
  any DB name that is not the one in DB_NAME env var if that matches
  the target (extra safety; the operator must pass --database explicitly).
- Reports each migration applied or skipped.
- The caller must pass --database; no default so a typo can never
  silently hit the production database.
- Never reads, prints or embeds the DB_PASSWORD value.

Safety rules enforced:
- Refuses to run if --database equals DB_NAME (from .env) unless you
  also pass --force (intended for CI that shares the name).
- Refuses to run if --database is empty.
- Statements that would fail with duplicate-key / duplicate-column /
  duplicate-index errors are treated as already-applied (idempotent
  on partial re-runs).
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the backend/ directory importable so dotenv loads .env
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv is optional; env vars may already be set

import pymysql


IDEMPOTENT_MYSQL_ERRORS = {
    1060,  # Duplicate column name
    1061,  # Duplicate key name (index)
    1050,  # Table already exists
    1826,  # Duplicate foreign key constraint name
    1630,  # Duplicate constraint name (MariaDB)
}

CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"""


def _connect(database: str) -> pymysql.Connection:
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database,
        autocommit=False,
        charset="utf8mb4",
    )


def _split_statements(sql: str) -> list[str]:
    """
    Split a SQL file into individual statements.
    Strips single-line (--) comments before splitting on semicolons.
    Skips USE and CREATE DATABASE statements (the runner already targets
    the correct database via the connection).
    """
    sql = re.sub(r"--[^\n]*", "", sql)
    statements = []
    for raw in sql.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue
        if re.match(r"(?i)^(USE|CREATE\s+DATABASE|DROP\s+DATABASE)\b", stmt):
            continue
        statements.append(stmt)
    return statements


def run_migrations(
    database: str,
    migrations_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Apply pending migrations to *database*.
    Returns the count of newly applied migrations.
    """
    real_db = os.getenv("DB_NAME", "fooddna")
    if database == real_db and not force:
        print(
            f"ERROR: --database '{database}' matches DB_NAME in your .env ({real_db}).\n"
            "Refusing to run — pass --force if you intentionally target that database.",
            file=sys.stderr,
        )
        sys.exit(2)

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print(f"No migration files found in {migrations_dir}")
        return 0

    conn = _connect(database)
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_MIGRATIONS_TABLE)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT filename FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}

        new_count = 0
        for sql_file in sql_files:
            filename = sql_file.name
            if filename in applied:
                print(f"  SKIP  {filename} (already applied)")
                continue

            print(f"  APPLY {filename}" + (" [DRY RUN]" if dry_run else ""))
            if dry_run:
                continue

            sql_text = sql_file.read_text(encoding="utf-8")
            statements = _split_statements(sql_text)

            errors = []
            with conn.cursor() as cur:
                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except pymysql.MySQLError as exc:
                        code = exc.args[0] if exc.args else 0
                        if code in IDEMPOTENT_MYSQL_ERRORS:
                            print(f"    WARN: idempotent error {code} — {exc.args[1] if len(exc.args) > 1 else exc}")
                        else:
                            errors.append(exc)
                            print(f"    ERROR in {filename}: {exc}", file=sys.stderr)

            if errors:
                conn.rollback()
                print(f"  ROLLED BACK {filename} due to {len(errors)} error(s).", file=sys.stderr)
                sys.exit(1)

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                )
            conn.commit()
            new_count += 1
            print(f"  DONE  {filename}")

        if new_count == 0:
            print("All migrations already applied — nothing to do.")
        else:
            print(f"\nApplied {new_count} migration(s) to '{database}'.")
        return new_count

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FoodDNA database migration runner."
    )
    parser.add_argument(
        "--database",
        required=True,
        help="Target database name (e.g. fooddna_dev). Required.",
    )
    parser.add_argument(
        "--migrations-dir",
        default=str(PROJECT_ROOT / "database" / "migrations"),
        help="Directory containing *.sql migration files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow targeting the production DB_NAME (use with extreme caution).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without applying them.",
    )
    args = parser.parse_args()

    if not args.database.strip():
        print("ERROR: --database cannot be empty.", file=sys.stderr)
        sys.exit(2)

    migrations_dir = Path(args.migrations_dir)
    if not migrations_dir.is_dir():
        print(f"ERROR: migrations directory not found: {migrations_dir}", file=sys.stderr)
        sys.exit(2)

    run_migrations(
        database=args.database.strip(),
        migrations_dir=migrations_dir,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
