from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, User, JournalEntry, GuidedResponse, ExerciseLog
from time_utils import register_template_utils
import os
import jinja2
import markupsafe

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class.
        
    Returns:
        Flask: Configured Flask application.
    """
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

    # Register time utilities for templates
    register_template_utils(app)    
    
    # Register blueprints
    from routes import auth_bp, journal_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    
    # Add custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ""
        return markupsafe.Markup(s.replace('\n', '<br>'))
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
