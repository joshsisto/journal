from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from models import db, User, JournalEntry, GuidedResponse, ExerciseLog
from time_utils import register_template_utils
import os
import jinja2
import markupsafe

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
mail = Mail()

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
    mail.init_app(app)

    # Register time utilities for templates
    register_template_utils(app)    
    
    # Register blueprints
    from routes import auth_bp, journal_bp, tag_bp, export_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(tag_bp, url_prefix='/tags')
    app.register_blueprint(export_bp, url_prefix='/export')
    
    # Add custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ""
        return markupsafe.Markup(s.replace('\n', '<br>'))
    
    # Add feeling emoji filter
    from helpers import get_feeling_emoji
    @app.template_filter('feeling_emoji')
    def feeling_emoji_filter(value):
        return get_feeling_emoji(value)
    
    # Add Python's built-in functions to templates
    app.jinja_env.globals.update(max=max)
    app.jinja_env.globals.update(min=min)
    
    # Add a filter to split strings
    @app.template_filter('split')
    def split_filter(s, delimiter=','):
        """Split a string by delimiter."""
        return s.split(delimiter)
    
    # Add custom test for checking if a variable exists    
    @app.template_test('defined')
    def is_defined(value):
        """Test if a variable is defined in the template."""
        return value is not None
        
    # Add Jinja2 helper functions
    @app.context_processor
    def utility_processor():
        """Add utility functions to the template context."""
        def parse_emotions(emotion_str):
            """Parse a JSON emotions string and return a list of emotions."""
            if not emotion_str or not isinstance(emotion_str, str):
                return []
                
            # Normalize the string to handle different formats
            emotion_str = emotion_str.strip()
            
            # If it already starts with [ it might be JSON
            if emotion_str.startswith('['):
                try:
                    import json
                    return json.loads(emotion_str)
                except:
                    # Simple fallback parser
                    clean_str = emotion_str.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
                    return [e.strip() for e in clean_str.split(',') if e.strip()]
            
            # If it has commas it might be a comma-separated string
            elif ',' in emotion_str:
                return [e.strip() for e in emotion_str.split(',') if e.strip()]
            
            # Just return a single item if it's a plain string
            elif emotion_str:
                return [emotion_str]
                
            return []
                
        return {'parse_emotions': parse_emotions}
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
