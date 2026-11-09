from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import Role, User
from app.utils.validation import (
    validate_confirm_password,
    validate_email,
    validate_full_name,
    validate_password
)
from werkzeug.security import generate_password_hash


def main():
    app = create_app()

    with app.app_context():
        print("Food DNA - Super Admin Initialization")
        print("--------------------------------------")

        full_name = input(
            "Super Admin full name: "
        ).strip()

        email = input(
            "Super Admin email: "
        ).strip().lower()

        password = getpass(
            "Super Admin password: "
        )

        confirm_password = getpass(
            "Confirm password: "
        )

        valid, message = validate_full_name(
            full_name
        )

        if not valid:
            print(message)
            return

        valid, message = validate_email(
            email
        )

        if not valid:
            print(message)
            return

        valid, message = validate_password(
            password
        )

        if not valid:
            print(message)
            return

        valid, message = validate_confirm_password(
            password,
            confirm_password
        )

        if not valid:
            print(message)
            return

        existing = User.query.filter_by(
            email=email
        ).first()

        if existing:
            print(
                "A user with this email already exists."
            )
            return

        role = Role.query.filter_by(
            name="super_admin"
        ).first()

        if role is None:
            print(
                "super_admin role does not exist."
            )
            print(
                "Run database/migrations/"
                "001_initial_schema.sql first."
            )
            return

        admin = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(
                password
            ),
            role_id=role.id,
            account_status="active",
            approval_status="not_required",
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()

        print()
        print(
            "Super Admin account created successfully."
        )


if __name__ == "__main__":
    main()