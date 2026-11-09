import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDER_SECRETS = {
    "",
    "development-secret-key-change-this",
    "change-this-to-a-random-secret-key",
}


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_database_uri(database_name=None):
    """
    Build the SQLAlchemy MySQL URL from environment variables.
    The password is read from .env and is never hard-coded.
    """
    return (
        f"mysql+pymysql://"
        f"{os.getenv('DB_USER', 'root')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '3306')}/"
        f"{database_name or os.getenv('DB_NAME', 'fooddna')}"
    )


class Config:
    # "development" or "production". Anything except "development"
    # is treated as production (the safer choice).
    ENVIRONMENT = os.getenv("FLASK_ENV", "production").strip().lower()

    SECRET_KEY = os.getenv("SECRET_KEY", "")

    APP_NAME = os.getenv("APP_NAME", "Food DNA")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JSON_SORT_KEYS = False

    # Session cookie security.
    # SESSION_COOKIE_SECURE must be True in production (HTTPS only).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Where the frontend is served from (used for reset links and CORS).
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

    # Origins allowed to call the API with cookies.
    # Comma-separated list. No wildcard and no "null" origin.
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5500,http://localhost:5500"
        ).split(",")
        if origin.strip()
    ]

    # Password reset
    PASSWORD_RESET_EXPIRY_MINUTES = int(
        os.getenv("PASSWORD_RESET_EXPIRY_MINUTES", "30")
    )

    # DEVELOPMENT ONLY: return the reset link in the API response because
    # no email service is configured. Always False in production.
    EXPOSE_DEV_RESET_LINK = ENVIRONMENT == "development"

    # Brute-force protection for login-style endpoints (per IP + email).
    AUTH_MAX_FAILED_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "8"))
    AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))

    # Phase 6: Documented and configurable flat delivery fee.
    DEFAULT_DELIVERY_FEE = os.getenv("DEFAULT_DELIVERY_FEE", "40.00")

    @classmethod
    def validate(cls):
        """Refuse to start in production with an unsafe secret key."""
        if cls.SECRET_KEY in _PLACEHOLDER_SECRETS:
            if cls.ENVIRONMENT != "development":
                raise RuntimeError(
                    "SECRET_KEY is missing or still a placeholder. "
                    "Set a long random SECRET_KEY in your .env file."
                )


class TestConfig(Config):
    """
    Used only by the automated tests.
    Points at a SEPARATE database so real data is never touched.
    """

    TESTING = True
    ENVIRONMENT = "development"
    SECRET_KEY = "test-secret-key-not-for-real-use"
    EXPOSE_DEV_RESET_LINK = True
    SQLALCHEMY_DATABASE_URI = build_database_uri(
        os.getenv("TEST_DB_NAME", "fooddna_test")
    )
    AUTH_MAX_FAILED_ATTEMPTS = 5
    AUTH_LOCKOUT_MINUTES = 15
