from flask import Flask, request, session, redirect, url_for, flash, current_app
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User, JournalEntry, GuidedResponse, ExerciseLog
from time_utils import register_template_utils
import logging
import os
import jinja2
import markupsafe
from datetime import timedelta
from security import setup_security, csp, talisman, limiter
from validators import sanitize_html, sanitize_text

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
mail = Mail()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

def create_app(config_class=Config):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class.
        
    Returns:
        Flask: Configured Flask application.
    """
    # Enable more detailed logging for debugging
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # Server name configuration has been removed
    
    # Set up basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Create upload folder if it doesn't exist
    upload_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    try:
        os.makedirs(upload_path, exist_ok=True)
    except OSError:
        pass
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    
    # Custom CSRF error handler for better debugging
    @app.errorhandler(400)
    def handle_csrf_error(e):
        current_app.logger.warning(f"CSRF validation failed: {e}")
        flash('Form submission failed. Please try again.', 'danger')
        return redirect(request.referrer or '/')
    
    # Configure session security
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('APP_URL', '').startswith('https://')
    
    # Configure CSRF protection (allow override for testing)
    if not app.config.get('WTF_CSRF_ENABLED') == False:  # Only override if not explicitly disabled
        app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
    app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow CSRF for proxied SSL
    app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']
    # Skip referrer check for proxy environments
    app.config['WTF_CSRF_CHECK_HEADERS'] = False
    # Configure trusted hosts for CSRF protection
    app.config['APPLICATION_ROOT'] = '/'
    
    # Set security-related configuration
    if not app.config.get('TESTING'):
        # In production, validate that secure secrets are used
        if app.config.get('SECRET_KEY') == 'dev-key-change-in-production':
            raise ValueError("SECRET_KEY must be changed from default value in production!")
        
        salt = os.environ.get('SECURITY_PASSWORD_SALT', 'change-me-in-production')
        if salt == 'change-me-in-production':
            raise ValueError("SECURITY_PASSWORD_SALT must be changed from default value in production!")
        app.config['SECURITY_PASSWORD_SALT'] = salt
    else:
        # In testing, use config value
        app.config['SECURITY_PASSWORD_SALT'] = app.config.get('SECURITY_PASSWORD_SALT', 'test-salt-for-testing-only')
    app.config['FORCE_HTTPS'] = app.config.get('APP_URL', '').startswith('https://')
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('FORCE_HTTPS', False)
    
    # Session security configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # 2 hour session timeout
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Configure upload limits
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    
    # Setup security features
    setup_security(app)
    
    # Apply request hook to log all requests
    @app.before_request
    def log_request_info():
        app.logger.debug('Request Headers: %s', request.headers)
        app.logger.debug('Request Path: %s', request.path)
        app.logger.debug('Request Method: %s', request.method)
        app.logger.debug('Request Remote Address: %s', request.remote_addr)
    
    # Apply request hook for automatic parameter sanitization
    @app.before_request
    def sanitize_request_data():
        # Sanitize URL parameters
        for key, value in list(request.args.items()):
            if key and value and isinstance(value, str):
                request.args = request.args.copy()
                request.args[key] = sanitize_text(value)
    
    # Apply security checks before each request
    @app.before_request
    def security_checks():
        # Block requests with suspicious SQL or script injection attempts
        if request.args:
            suspicious_patterns = [
                "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", 
                "UNION", "1=1", "--", "<script>", "eval(", "javascript:"
            ]
            
            for key, value in request.args.items():
                if isinstance(value, str):
                    value_upper = value.upper()
                    for pattern in suspicious_patterns:
                        if pattern.upper() in value_upper:
                            app.logger.warning(f'Blocked suspicious request with parameter {key}={value[:50]}')
                            return "Bad request", 400

    # Register time utilities for templates
    register_template_utils(app)    
    
    # Register blueprints
    from routes import auth_bp, journal_bp, tag_bp, export_bp, ai_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(tag_bp, url_prefix='/tags')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    
    # Rate limits are applied directly on the route functions
    # No need to apply them here
    
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
        
    # Add datetime formatting filter
    @app.template_filter('format_datetime')
    def format_datetime_filter(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)
    
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
        import secrets
        
        # CSRF token is already generated in security.py
        
        def csrf_token():
            """Return the CSRF token for forms."""
            from flask_wtf.csrf import generate_csrf
            return generate_csrf()
            
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
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Simple fallback parser for malformed JSON
                    clean_str = emotion_str.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
                    return [e.strip() for e in clean_str.split(',') if e.strip()]
            
            # If it has commas it might be a comma-separated string
            elif ',' in emotion_str:
                return [e.strip() for e in emotion_str.split(',') if e.strip()]
            
            # Just return a single item if it's a plain string
            elif emotion_str:
                return [emotion_str]
                
            return []
                
        return {'parse_emotions': parse_emotions, 'csrf_token': csrf_token}
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Run without SSL for testing (this should fix AI conversation issues)
    #app.run(host="0.0.0.0", debug=True)
    
    # For HTTPS (needed for camera access from non-localhost)
    app.run(host="0.0.0.0", debug=False, ssl_context='adhoc')
    
    # For production with proper certificates:
    # app.run(host="0.0.0.0", ssl_context=('cert.pem', 'key.pem'))
