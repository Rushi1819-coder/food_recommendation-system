"""
FoodDNA - Application Factory.

Initialises extensions, registers route blueprints, sets up CORS,
and configures standard JSON error handlers.
"""

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .extensions import cors, db
from .routes.auth import auth_bp
from .routes.cart import cart_bp
from .routes.food_memory import food_memory_bp
from .routes.meals import categories_bp, meals_bp
from .routes.orders import orders_bp
from .routes.operations import operations_bp
from .routes.engagement import engagement_bp
from .routes.preferences import preferences_bp
from .routes.recommendations import recommendations_bp
from .routes.restaurants import restaurants_bp
from .routes.user import user_bp


def create_app(config_class=Config):
    """Create and configure the Flask application instance."""
    config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialise SQLAlchemy database
    db.init_app(app)

    # Configure Cross-Origin Resource Sharing
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CORS_ORIGINS", [])
            }
        },
        supports_credentials=True,
    )

    # Register blueprints across implemented core and operations phases (Phases 1-10)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(meals_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(food_memory_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(engagement_bp)

    @app.get("/")
    def home():
        return jsonify({
            "success": True,
            "application": app.config["APP_NAME"],
            "version": app.config["APP_VERSION"],
            "message": "Food DNA backend is running.",
        })

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "success": True,
            "status": "healthy",
            "service": "Food DNA API",
        })

    @app.get("/api/health/db")
    def database_health_check():
        """Check that the configured database connection can execute a query."""
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({
                "success": True,
                "status": "database_ok",
                "service": "Food DNA database",
            }), 200
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Database health check failed")
            return jsonify({
                "success": False,
                "status": "database_error",
                "error": "Database connection failed.",
            }), 503

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": "Bad request.",
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "success": False,
            "error": "Authentication required.",
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "success": False,
            "error": "Access denied.",
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Resource not found.",
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "success": False,
            "error": "Method not allowed.",
        }), 405

    @app.errorhandler(409)
    def conflict(error):
        return jsonify({
            "success": False,
            "error": "Resource conflict.",
        }), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "A database error occurred.",
        }), 500

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Internal server error.",
        }), 500

    return app
