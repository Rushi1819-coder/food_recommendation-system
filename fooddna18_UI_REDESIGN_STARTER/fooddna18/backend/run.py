import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    # Debug mode is controlled by FLASK_DEBUG in .env (1 = on).
    # Never run with debug on in production.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
