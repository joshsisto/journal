"""
Security utilities for the application.

This module provides functions and classes to enhance application security,
including CSP settings, rate limiting, and CSRF protection.
"""
from flask import session, request, abort, current_app
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import functools
import re
from validators import sanitize_text

# Initialize CSP settings
csp = {
    'default-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'code.jquery.com',
        'cdn.jsdelivr.net',
    ],
    'script-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'code.jquery.com',
        '\'unsafe-inline\'',
        '\'unsafe-eval\'',
    ],
    'style-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        '\'unsafe-inline\'',
    ],
    'img-src': [
        '\'self\'',
        'data:',
        '*',  # Allow images from anywhere
    ],
    'font-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
    ],
    'connect-src': [
        '\'self\'',
    ],
}

# Create Talisman instance
talisman = Talisman(content_security_policy=csp, force_https=False)

# Create Limiter with default limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)

# Security decorators and helpers

# CSRF protection is now handled by Flask-WTF automatically

def sanitize_params():
    """
    Decorator to sanitize URL parameters.
    
    Returns:
        decorator: Function decorator
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Sanitize URL parameters
            for key, value in list(request.args.items()):
                if value:
                    clean_value = sanitize_text(value)
                    if clean_value != value:
                        # Modify request args if sanitized value is different
                        args_dict = request.args.copy()
                        args_dict[key] = clean_value
                        request.args = args_dict
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_authorization(f):
    """
    Decorator to validate user authorization for a resource.
    
    This checks if the current user has access to the requested resource
    (e.g., journal entry, tag, etc.)
    
    Returns:
        decorator: Function decorator
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from models import JournalEntry, Tag, Photo
        
        # Check if this involves an entry ID
        entry_id = kwargs.get('entry_id')
        if entry_id:
            entry = JournalEntry.query.get(entry_id)
            if not entry or entry.user_id != current_user.id:
                abort(403)  # Forbidden
        
        # Check if this involves a tag ID
        tag_id = kwargs.get('tag_id') or request.args.get('tag')
        if tag_id:
            try:
                tag_id = int(tag_id)
                tag = Tag.query.get(tag_id)
                if tag and tag.user_id != current_user.id:
                    abort(403)  # Forbidden
            except (ValueError, TypeError):
                pass
        
        # Check if this involves a photo ID
        photo_id = kwargs.get('photo_id')
        if photo_id:
            photo = Photo.query.join(JournalEntry).filter(
                Photo.id == photo_id
            ).first()
            
            if not photo or photo.journal_entry.user_id != current_user.id:
                abort(403)  # Forbidden
        
        return f(*args, **kwargs)
    return decorated_function

def setup_security(app):
    """
    Set up security features for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Initialize rate limiting - don't set specific limits here
    # We'll set them in app.py after blueprints are registered
    limiter.init_app(app)
    
    # We won't use Talisman for now as it can cause issues with the app
    # talisman.init_app(
    #     app,
    #     content_security_policy=csp,
    #     content_security_policy_nonce_in=['script-src'],
    #     force_https=app.config.get('FORCE_HTTPS', False),
    #     session_cookie_secure=app.config.get('SESSION_COOKIE_SECURE', False),
    #     session_cookie_http_only=True,
    #     feature_policy={
    #         'geolocation': '\'none\'',
    #         'camera': '\'self\'',  # Allow camera access from same origin
    #         'microphone': '\'none\'',
    #     }
    # )
    
    # Setup basic security headers
    @app.after_request
    def set_secure_headers(response):
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Flask-WTF will handle CSRF token generation automatically
    
    # Log security events
    @app.before_request
    def log_suspicious_activity():
        # Check for SQL injection attempts
        sql_injection_pattern = re.compile(r'(\bSELECT\b|\bUNION\b|\bINSERT\b|\bDROP\b|\bDELETE\b|\bUPDATE\b|\b1=1\b|--[^\n]*$)', re.IGNORECASE)
        
        # Check URL and form data for suspicious patterns
        for key, value in list(request.args.items()):
            if isinstance(value, str) and sql_injection_pattern.search(value):
                app.logger.warning(f'Possible SQL injection attempt in URL params from {request.remote_addr}: {key}={value}')
                # Don't abort here but log the attempt
        
        if request.method == 'POST' and request.form:
            for key, value in request.form.items():
                if key.lower() in ('password', 'new_password', 'confirm_password', 'current_password'):
                    # Skip password fields for privacy
                    continue
                
                if isinstance(value, str) and sql_injection_pattern.search(value):
                    app.logger.warning(f'Possible SQL injection attempt in form data from {request.remote_addr}: {key}={value[:50]}...')
                    # Don't abort here but log the attempt