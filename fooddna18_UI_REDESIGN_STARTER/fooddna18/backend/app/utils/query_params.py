"""Validation helpers for public query-string parameters."""

import re
from decimal import Decimal, InvalidOperation

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50
MAX_TEXT_LENGTH = 100
MAX_PRICE = Decimal("9999999.99")

# Plain decimal notation only: "120", "120.5", "120.50"
# (no exponent, sign, spaces or underscores).
PRICE_PATTERN = re.compile(r"^\d{1,7}(\.\d{1,2})?$")


class QueryParamError(ValueError):
    """Raised for an invalid query parameter; the message is user-safe."""


def parse_positive_int(raw, name):
    """Return an int >= 1, or None when the parameter is absent/blank."""
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    if not (raw.isascii() and raw.isdigit()) or len(raw) > 18:
        raise QueryParamError(f"{name} must be a positive whole number.")
    value = int(raw)
    if value < 1:
        raise QueryParamError(f"{name} must be a positive whole number.")
    return value


def parse_text(raw, name):
    """Trimmed text (max 100 chars, no control characters) or None."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    if len(raw) > MAX_TEXT_LENGTH:
        raise QueryParamError(
            f"{name} must be at most {MAX_TEXT_LENGTH} characters."
        )
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise QueryParamError(f"{name} contains invalid characters.")
    return raw


def parse_price(raw, name):
    """Return a Decimal in [0, 9999999.99] with at most 2 decimals, or None."""
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    if raw.startswith("-"):
        raise QueryParamError(f"{name} cannot be negative.")
    if not (raw.isascii() and PRICE_PATTERN.fullmatch(raw)):
        raise QueryParamError(
            f"{name} must be a plain number with at most 2 decimal places."
        )
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise QueryParamError(f"{name} must be a valid number.")
    if value > MAX_PRICE:
        raise QueryParamError(f"{name} is out of range.")
    return value


def parse_pagination(args):
    """Return (page, page_size) with validation."""
    page = parse_positive_int(args.get("page"), "page") or 1
    page_size = (
        parse_positive_int(args.get("page_size"), "page_size")
        or DEFAULT_PAGE_SIZE
    )
    if page_size > MAX_PAGE_SIZE:
        raise QueryParamError(f"page_size must be at most {MAX_PAGE_SIZE}.")
    if page > 1_000_000:
        raise QueryParamError("page is out of range.")
    return page, page_size


def escape_like(text):
    """Escape LIKE wildcards so user text is matched literally."""
    return (
        text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def pagination_block(page, page_size, total):
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }
