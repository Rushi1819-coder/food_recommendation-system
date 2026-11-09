import re
import unicodedata

NAME_MAX_LENGTH = 120
EMAIL_MAX_LENGTH = 254

# New account emails must use Gmail. Keep a normal email-style local part, but
# require the domain to be exactly gmail.com (not gmail.co or another provider).
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?@gmail\.com$",
    re.IGNORECASE,
)

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Z])"
    r"(?=.*[a-z])"
    r"(?=.*\d)"
    r"(?=.*[^A-Za-z0-9])"
    r"\S{8,}$"
)


def validate_full_name(full_name):
    """
    Accepts Unicode letters and spaces only. Rejects digits, punctuation,
    control characters, symbols, empty values and over-long input.
    """
    if not isinstance(full_name, str):
        return False, "Full name is required."

    full_name = full_name.strip()

    if not full_name:
        return False, "Full name is required."

    if len(full_name) > NAME_MAX_LENGTH:
        return (
            False,
            f"Full name must be at most {NAME_MAX_LENGTH} characters."
        )

    letters = 0
    for ch in full_name:
        category = unicodedata.category(ch)
        if category.startswith("L"):
            letters += 1
        elif category.startswith("M") or ch == " ":
            # Combining marks allow accented letters and several scripts.
            continue
        else:
            # digits, control characters, symbols, emoji, etc.
            return (
                False,
                "Full name may contain only letters and spaces."
            )

    if letters == 0:
        return False, "Full name must contain at least one letter."

    return True, ""


def validate_email(email):
    if not isinstance(email, str):
        return False, "Email is required."

    email = email.strip().lower()

    if (
        len(email) > EMAIL_MAX_LENGTH
        or ".." in email
        or not EMAIL_PATTERN.fullmatch(email)
    ):
        return False, "Please enter a valid Gmail address ending in @gmail.com."

    return True, ""


def validate_password(password):
    if not isinstance(password, str):
        return False, "Password is required."

    if not PASSWORD_PATTERN.fullmatch(password):
        return (
            False,
            "Password must contain at least 8 characters, "
            "one uppercase letter, one lowercase letter, "
            "one number, one special character, "
            "and no spaces."
        )

    return True, ""


def validate_confirm_password(password, confirm_password):
    if password != confirm_password:
        return False, "Passwords do not match."

    return True, ""