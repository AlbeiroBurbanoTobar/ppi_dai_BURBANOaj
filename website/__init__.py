from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

# Database instance (global for convenience in this example)
db = SQLAlchemy()

# Database name constant
DB_NAME = "database.db"


def create_app():
    """Creates a Flask application instance with database configuration.

    Returns:
        Flask: A configured Flask application.
    """

    app = Flask(__name__)

    # Secret key for session management (replace with a strong random value)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'

    # Database URI configuration (consider using environment variables for security)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Import blueprints from views and auth modules
    from .views import views
    from .auth import auth

    # Register blueprints with URL prefixes
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Import models (assuming User and Note are defined elsewhere)
    from .models import User, Note

    # Create database tables if they don't exist (within application context)
    with app.app_context():
        db.create_all()

    # Configure LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # User loader function for LoginManager
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    """Creates the database if it doesn't exist.

    Args:
        app (Flask): The Flask application instance.
    """

    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
