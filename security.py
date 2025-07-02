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
    
    # Initialize Talisman for enhanced security headers (if enabled)
    if app.config.get('TALISMAN_ENABLED', True):
        talisman.init_app(
            app,
            content_security_policy=csp,
            content_security_policy_nonce_in=['script-src'],
            force_https=app.config.get('FORCE_HTTPS', False),
            session_cookie_secure=app.config.get('SESSION_COOKIE_SECURE', False),
            session_cookie_http_only=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            strict_transport_security_include_subdomains=True,
            feature_policy={
                'geolocation': '\'none\'',
                'camera': '\'self\'',  # Allow camera access from same origin
                'microphone': '\'none\'',
                'payment': '\'none\'',
                'usb': '\'none\'',
            }
        )
    
    # Setup basic security headers
    @app.after_request
    def set_secure_headers(response):
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Flask-WTF will handle CSRF token generation automatically
    
    # Enhanced security monitoring
    @app.before_request
    def monitor_suspicious_activity():
        # Enhanced SQL injection patterns
        sql_injection_pattern = re.compile(
            r'(\bSELECT\b|\bUNION\b|\bINSERT\b|\bDROP\b|\bDELETE\b|\bUPDATE\b|\bALTER\b|\bCREATE\b|\bEXEC\b|\b1=1\b|--[^\n]*$|\bOR\s+\d+=\d+\b|\bAND\s+\d+=\d+\b|\'.*\'|\".*\"|;|\\\x27|\\\x22|\\\x5C)', 
            re.IGNORECASE
        )
        
        # XSS patterns
        xss_pattern = re.compile(
            r'(<script|javascript:|on\w+\s*=|<iframe|<object|<embed|\balert\s*\(|\bconfirm\s*\(|\bprompt\s*\()',
            re.IGNORECASE
        )
        
        suspicious_request = False
        
        # Check URL parameters
        for key, value in list(request.args.items()):
            if isinstance(value, str):
                if sql_injection_pattern.search(value):
                    app.logger.warning(f'SQL injection attempt blocked from {request.remote_addr}: {key}={value[:100]}')
                    suspicious_request = True
                elif xss_pattern.search(value):
                    app.logger.warning(f'XSS attempt blocked from {request.remote_addr}: {key}={value[:100]}')
                    suspicious_request = True
        
        # Check form data
        if request.method == 'POST' and request.form:
            for key, value in request.form.items():
                # Skip fields that should not be validated for security patterns
                if key.lower() in ('password', 'new_password', 'confirm_password', 'current_password'):
                    continue  # Skip password fields
                
                # Skip emotion fields that contain legitimate JSON data
                if key.startswith('question_') and 'emotion' in key.lower():
                    continue  # Skip emotion JSON fields
                
                # Skip other legitimate JSON fields
                if key in ('new_tags',):
                    continue  # Skip JSON tag data
                
                if isinstance(value, str):
                    if sql_injection_pattern.search(value):
                        app.logger.warning(f'SQL injection attempt blocked from {request.remote_addr}: {key}={value[:100]}')
                        suspicious_request = True
                    elif xss_pattern.search(value) and key not in ('content', 'response'):  # Allow some HTML in content fields
                        app.logger.warning(f'XSS attempt blocked from {request.remote_addr}: {key}={value[:100]}')
                        suspicious_request = True
        
        # Block suspicious requests
        if suspicious_request:
            abort(400, description="Malicious input detected")