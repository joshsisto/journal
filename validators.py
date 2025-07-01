"""
Validators and security functions for handling user input.

This module provides utility functions to validate and sanitize user input
to protect against common web vulnerabilities like XSS, CSRF, SQLi, etc.
"""
import re
import bleach
import json
from wtforms.validators import ValidationError
from marshmallow import Schema, fields, validate, ValidationError as MarshmallowValidationError
from pydantic import BaseModel, Field, EmailStr, constr, validator
import functools

# Configure bleach settings for HTML sanitization
ALLOWED_TAGS = {
    'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'p', 'ul', 'ol', 
    'li', 'br', 'sub', 'sup', 'hr', 'blockquote', 'span', 'code'
}

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'span': ['style'],
}

# Regular expressions for validation
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
# Simplified password regex - at least 8 chars with at least one letter and one number
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$')
# More permissive email regex that allows for a wider range of valid email formats
EMAIL_REGEX = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
TAG_NAME_REGEX = re.compile(r'^[a-zA-Z0-9 _-]{1,50}$')
COLOR_HEX_REGEX = re.compile(r'^#[0-9a-fA-F]{6}$')

# Maximum lengths for text inputs
MAX_USERNAME_LENGTH = 30
MAX_PASSWORD_LENGTH = 100
MAX_EMAIL_LENGTH = 120
MAX_JOURNAL_CONTENT_LENGTH = 10000  # 10KB
MAX_TAG_NAME_LENGTH = 50
MAX_EMOTION_TEXT_LENGTH = 100
MAX_QUESTION_RESPONSE_LENGTH = 5000

# Sanitization functions

def sanitize_text(text, max_length=None):
    """
    Sanitize plain text by removing special characters.
    
    Args:
        text (str): Text to sanitize
        max_length (int, optional): Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)
    
    # Trim to max length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    # Remove any potentially harmful characters
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
    
    return text.strip()

def sanitize_html(html_content, max_length=None):
    """
    Sanitize HTML content to prevent XSS attacks.
    
    Args:
        html_content (str): HTML content to sanitize
        max_length (int, optional): Maximum allowed length
        
    Returns:
        str: Sanitized HTML
    """
    if not html_content:
        return ""
    
    # Convert to string if not already
    if not isinstance(html_content, str):
        html_content = str(html_content)
    
    # Trim to max length if specified
    if max_length and len(html_content) > max_length:
        html_content = html_content[:max_length]
    
    # Use bleach to clean the HTML
    cleaned = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    return cleaned

def sanitize_username(username):
    """
    Sanitize and validate username.
    
    Args:
        username (str): Username to sanitize
        
    Returns:
        str: Sanitized username
        
    Raises:
        ValidationError: If username is invalid
    """
    if not username:
        raise ValidationError('Username is required')
    
    username = sanitize_text(username, MAX_USERNAME_LENGTH)
    
    if not USERNAME_REGEX.match(username):
        raise ValidationError('Username must be 3-30 characters and can only contain letters, numbers, underscores, and hyphens')
    
    return username

def sanitize_email(email):
    """
    Sanitize and validate email.
    
    Args:
        email (str): Email to sanitize
        
    Returns:
        str: Sanitized email or None if empty
        
    Raises:
        ValidationError: If email is invalid
    """
    # Handle None or empty string
    if not email or email.strip() == '':
        return None  # Email is optional
    
    # Basic cleanup - just trim whitespace and convert to lowercase
    email = email.strip().lower()
    
    # Limit length
    if len(email) > MAX_EMAIL_LENGTH:
        email = email[:MAX_EMAIL_LENGTH]
    
    # Basic format check
    if not EMAIL_REGEX.match(email):
        raise ValidationError('Please enter a valid email address')
    
    return email

def validate_password(password):
    """
    Validate password strength with enhanced security requirements.
    
    Args:
        password (str): Password to validate
        
    Returns:
        bool: True if password is valid
        
    Raises:
        ValidationError: If password is invalid
    """
    if not password:
        raise ValidationError('Password is required')
    
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long')
    
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f'Password cannot exceed {MAX_PASSWORD_LENGTH} characters')
    
    # Enhanced password complexity requirements
    has_lower = False
    has_upper = False
    has_number = False
    has_special = False
    
    special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?~`')
    
    for char in password:
        if char.islower():
            has_lower = True
        elif char.isupper():
            has_upper = True
        elif char.isdigit():
            has_number = True
        elif char in special_chars:
            has_special = True
    
    # Check complexity requirements
    if not has_lower:
        raise ValidationError('Password must contain at least one lowercase letter')
    if not has_upper:
        raise ValidationError('Password must contain at least one uppercase letter')
    if not has_number:
        raise ValidationError('Password must contain at least one number')
    if not has_special:
        raise ValidationError('Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?~`)')
    
    # Check against common passwords list from config
    from flask import current_app
    try:
        common_passwords = current_app.config.get('COMMON_PASSWORDS', set())
    except RuntimeError:
        # Fallback for when called outside application context
        from config import Config
        common_passwords = Config.COMMON_PASSWORDS
    
    if password.lower() in common_passwords:
        raise ValidationError('Password is too common. Please choose a stronger password.')
    
    # Check for simple patterns
    if password.lower() in password.lower():  # redundant check, but keeps structure
        # Check for keyboard patterns
        keyboard_patterns = ['qwerty', 'asdf', '1234', 'abcd']
        for pattern in keyboard_patterns:
            if pattern in password.lower():
                raise ValidationError('Password contains common keyboard patterns. Please choose a more complex password.')
    
    return True

def sanitize_tag_name(tag_name):
    """
    Sanitize and validate tag name.
    
    Args:
        tag_name (str): Tag name to sanitize
        
    Returns:
        str: Sanitized tag name
        
    Raises:
        ValidationError: If tag name is invalid
    """
    if not tag_name:
        raise ValidationError('Tag name is required')
    
    tag_name = sanitize_text(tag_name, MAX_TAG_NAME_LENGTH)
    
    if not TAG_NAME_REGEX.match(tag_name):
        raise ValidationError('Tag name can only contain letters, numbers, spaces, underscores, and hyphens')
    
    return tag_name

def validate_color_hex(color):
    """
    Validate color hex code.
    
    Args:
        color (str): Color hex to validate
        
    Returns:
        str: Validated color hex
        
    Raises:
        ValidationError: If color hex is invalid
    """
    if not color:
        return "#6c757d"  # Default color if not provided
    
    if not COLOR_HEX_REGEX.match(color):
        raise ValidationError('Color must be a valid hex code (e.g., #FF5733)')
    
    return color

def sanitize_journal_content(content):
    """
    Sanitize journal entry content.
    
    Args:
        content (str): Journal content to sanitize
        
    Returns:
        str: Sanitized content
    """
    if not content:
        return ""
    
    # For journal content, we'll allow a wider range of characters
    # but still sanitize HTML and limit length
    return sanitize_html(content, MAX_JOURNAL_CONTENT_LENGTH)

def sanitize_question_response(response):
    """
    Sanitize guided journal question response.
    
    Args:
        response (str): Response to sanitize
        
    Returns:
        str: Sanitized response
    """
    if not response:
        return ""
    
    return sanitize_text(response, MAX_QUESTION_RESPONSE_LENGTH)

def validate_guided_response_json(json_str):
    """
    Validate and sanitize JSON data from guided response fields.
    
    Args:
        json_str (str): JSON string to validate
        
    Returns:
        dict: Validated and sanitized JSON data
        
    Raises:
        ValidationError: If JSON is invalid or contains malicious content
    """
    if not json_str:
        return {}
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValidationError('Invalid JSON format in guided response')
    
    if not isinstance(data, dict):
        raise ValidationError('Guided response must be a JSON object')
    
    # Validate and sanitize specific fields
    validated_data = {}
    
    # Validate emotions field
    if 'emotions' in data:
        emotions = data['emotions']
        if isinstance(emotions, list):
            valid_emotions = []
            for emotion in emotions:
                if isinstance(emotion, str) and len(emotion) <= MAX_EMOTION_TEXT_LENGTH:
                    # Sanitize emotion text
                    clean_emotion = sanitize_text(emotion)
                    if clean_emotion:
                        valid_emotions.append(clean_emotion)
                elif isinstance(emotion, dict) and 'name' in emotion:
                    # Handle emotion objects
                    emotion_name = sanitize_text(str(emotion['name']))
                    if emotion_name and len(emotion_name) <= MAX_EMOTION_TEXT_LENGTH:
                        valid_emotions.append(emotion_name)
            validated_data['emotions'] = valid_emotions[:20]  # Limit to 20 emotions
    
    # Validate feeling_scale field
    if 'feeling_scale' in data:
        feeling_scale = data['feeling_scale']
        if isinstance(feeling_scale, (int, float)):
            if 1 <= feeling_scale <= 10:
                validated_data['feeling_scale'] = int(feeling_scale)
            else:
                raise ValidationError('Feeling scale must be between 1 and 10')
        elif isinstance(feeling_scale, str) and feeling_scale.isdigit():
            scale_val = int(feeling_scale)
            if 1 <= scale_val <= 10:
                validated_data['feeling_scale'] = scale_val
            else:
                raise ValidationError('Feeling scale must be between 1 and 10')
    
    # Validate response text fields
    for field in ['question_feeling_reason', 'question_about_day', 'question_anything_else']:
        if field in data:
            response_text = data[field]
            if isinstance(response_text, str):
                validated_data[field] = sanitize_question_response(response_text)
    
    # Validate custom fields but limit their size and number
    custom_field_count = 0
    for key, value in data.items():
        if key not in ['emotions', 'feeling_scale', 'question_feeling_reason', 'question_about_day', 'question_anything_else']:
            if custom_field_count >= 10:  # Limit custom fields
                break
            
            if isinstance(value, str) and len(value) <= MAX_QUESTION_RESPONSE_LENGTH:
                validated_data[key] = sanitize_text(value)
                custom_field_count += 1
            elif isinstance(value, (int, float)) and -1000000 <= value <= 1000000:
                validated_data[key] = value
                custom_field_count += 1
    
    return validated_data

def validate_json_structure(json_str, expected_schema=None):
    """
    Validate JSON structure and content safety.
    
    Args:
        json_str (str): JSON string to validate
        expected_schema (dict, optional): Expected schema structure
        
    Returns:
        dict: Validated JSON data
        
    Raises:
        ValidationError: If JSON is invalid or unsafe
    """
    if not json_str:
        return {}
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValidationError(f'Invalid JSON format: {str(e)}')
    
    # Check for deeply nested structures (potential DoS)
    def check_depth(obj, max_depth=10, current_depth=0):
        if current_depth > max_depth:
            raise ValidationError('JSON structure too deeply nested')
        
        if isinstance(obj, dict):
            for value in obj.values():
                check_depth(value, max_depth, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, max_depth, current_depth + 1)
    
    check_depth(data)
    
    # Check for excessively large arrays or objects
    def check_size(obj, max_items=100):
        if isinstance(obj, dict):
            if len(obj) > max_items:
                raise ValidationError('JSON object too large')
            for value in obj.values():
                check_size(value, max_items)
        elif isinstance(obj, list):
            if len(obj) > max_items:
                raise ValidationError('JSON array too large')
            for item in obj:
                check_size(item, max_items)
    
    check_size(data)
    
    return data

# Pydantic models for request validation

class RegisterSchema(BaseModel):
    """Schema for user registration data validation."""
    username: constr(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_-]+$')
    email: str = None  # Make email optional
    password: constr(min_length=8, max_length=100)
    timezone: str = 'UTC'
    
    @validator('email')
    def validate_optional_email(cls, v):
        """Allow None or empty string for email."""
        if v is None or v == "":
            return None
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if not USERNAME_REGEX.match(v):
            raise ValueError('Username must be 3-30 characters and can only contain letters, numbers, underscores, and hyphens')
        return v
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not PASSWORD_REGEX.match(v):
            raise ValueError('Password must contain at least one letter and one number')
        return v

class LoginSchema(BaseModel):
    """Schema for login data validation."""
    username: str
    password: str
    remember: bool = False

class QuickJournalSchema(BaseModel):
    """Schema for quick journal entry validation."""
    content: constr(max_length=MAX_JOURNAL_CONTENT_LENGTH)
    tags: list = []
    new_tags: str = "[]"

class TagSchema(BaseModel):
    """Schema for tag validation."""
    name: constr(min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9 _-]+$')
    color: constr(pattern=r'^#[0-9a-fA-F]{6}$') = "#6c757d"

# Flask route decorators for validation

def validate_form(schema_class):
    """
    Decorator to validate form data using a Pydantic schema.
    
    Args:
        schema_class: Pydantic model class to use for validation
        
    Returns:
        decorator: Function decorator
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, flash, redirect, url_for
            
            if request.method == 'POST':
                try:
                    # Validate form data against schema
                    data = {key: value for key, value in request.form.items()}
                    validated_data = schema_class(**data)
                    
                    # Add validated data to kwargs
                    kwargs['validated_data'] = validated_data
                    
                except ValueError as e:
                    # Handle validation errors
                    flash(str(e), 'danger')
                    return redirect(request.url)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(f):
    """
    Decorator to sanitize request input data.
    
    Args:
        f: Function to decorate
        
    Returns:
        decorated_function: Decorated function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        
        if request.method == 'POST':
            # Sanitize form data
            for key in request.form:
                if key == 'password' or key == 'current_password' or key == 'new_password' or key == 'confirm_password':
                    # Skip password fields
                    continue
                
                value = request.form[key]
                if key in ['content', 'response', 'question_feeling_reason', 'question_about_day', 'question_anything_else']:
                    # HTML content fields
                    request.form = request.form.copy()
                    request.form[key] = sanitize_journal_content(value)
                else:
                    # Regular text fields
                    request.form = request.form.copy()
                    request.form[key] = sanitize_text(value)
        
        return f(*args, **kwargs)
    return decorated_function

# Rate limiting helpers

def get_remote_address():
    """
    Get the remote address (IP) of the current request.
    
    Returns:
        str: IP address
    """
    from flask import request
    
    # Check for proxy headers first (X-Forwarded-For)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    return request.remote_addr