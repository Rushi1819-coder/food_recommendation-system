"""
Create and initialise a SEPARATE development database (default: fooddna_dev).

Why a script instead of piping schema.sql into mysql?
database/schema.sql and the migrations contain "USE fooddna;", so piping
them into MySQL would always build tables in the real `fooddna` database,
no matter what DB_NAME says. This script applies the same SQL files but
skips the CREATE DATABASE / USE lines and runs them inside the development
database instead.

Safe to re-run: the SQL uses CREATE TABLE IF NOT EXISTS and upserts. It
never drops, truncates or deletes anything, and it refuses any database
whose name does not end in "_dev" or that is called "fooddna".

Usage (from the backend folder, virtual environment active):
    python init_dev_database.py            # creates/initialises fooddna_dev
    python init_dev_database.py my_other_dev
"""

import os
import re
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NAME = "fooddna_dev"
NAME_RE = re.compile(r"^[A-Za-z0-9_]+_dev$")


def check_database_name(name):
    if (name or "").lower() == "fooddna" or not NAME_RE.fullmatch(name or ""):
        raise ValueError(
            f"Refusing '{name}': the development database name must "
            "contain only letters, digits and underscores, and end in '_dev'."
        )


def split_sql(text):
    """Split an SQL file into statements (the files contain no ';' in text)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


def sql_files():
    files = [PROJECT_ROOT / "database" / "schema.sql"]
    files += sorted((PROJECT_ROOT / "database" / "migrations").glob("*.sql"))
    return files


def connect(database=None):
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database,
        autocommit=True,
    )


def initialise(name):
    check_database_name(name)

    admin = connect()
    with admin.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    admin.close()

    conn = connect(name)
    applied = 0
    with conn.cursor() as cur:
        for path in sql_files():
            for statement in split_sql(path.read_text(encoding="utf-8")):
                if re.match(r"(?i)^(CREATE DATABASE|USE)\b", statement):
                    continue
                try:
                    cur.execute(statement)
                    applied += 1
                except pymysql.MySQLError as err:
                    # Error 1061: Duplicate key name / constraint already exists.
                    # Safe to ignore when re-running migrations.
                    if getattr(err, "args", [None])[0] in {1061, 1060, 1826}:
                        continue
                    raise
        cur.execute("SHOW TABLES")
        tables = len(cur.fetchall())
    conn.close()
    return tables, applied


def main(argv):
    name = argv[1] if len(argv) > 1 else DEFAULT_NAME
    try:
        tables, applied = initialise(name)
    except ValueError as error:
        print(f"\nREFUSED: {error}\n")
        return 2
    except pymysql.MySQLError as error:
        print(
            f"\nFAILED: {error}\nIs MySQL running, and are DB_USER / "
            "DB_PASSWORD in your .env correct?\n"
        )
        return 1

    print(
        f"Database '{name}' is ready: {tables} tables "
        f"({applied} SQL statements applied)."
    )
    print(
        "Next: set DB_NAME for this PowerShell window, then run "
        "python seed_demo_data.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
