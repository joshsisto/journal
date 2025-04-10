"""
Temporary app using the original models to fix the database.

This simplified app will only allow you to recreate the database schema.
"""
from flask import Flask
from flask_login import LoginManager
from config import Config
import os

# Import the original models without the new fields
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("models_original", "./models_original.py")
models_original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_original)

# Use the original models
db = models_original.db
User = models_original.User

login_manager = LoginManager()
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_temp_app(config_class=Config):
    """Create a temporary Flask application for database setup."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Just a simple route to test
    @app.route('/')
    def index():
        return "Temporary app for database setup. Please use recreate_db.py instead."
    
    # Create database tables
    with app.app_context():
        db.create_all()
        print("Database tables created using original models.")
    
    return app

if __name__ == '__main__':
    app = create_temp_app()
    print("NOTE: This is a temporary app. Use recreate_db.py for proper setup.")
    app.run(debug=True, port=5001)