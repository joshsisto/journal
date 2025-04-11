"""
Validators and security functions for handling user input.

This module provides utility functions to validate and sanitize user input
to protect against common web vulnerabilities like XSS, CSRF, SQLi, etc.
"""
import re
import bleach
from html_sanitizer import Sanitizer
from wtforms.validators import ValidationError
from marshmallow import Schema, fields, validate, ValidationError as MarshmallowValidationError
from pydantic import BaseModel, Field, EmailStr, constr, validator
import functools

# Configure HTML sanitizer with safe settings
sanitizer = Sanitizer({
    'tags': {
        'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'p', 'ul', 'ol', 
        'li', 'br', 'sub', 'sup', 'hr', 'blockquote', 'span', 'code'
    },
    'attributes': {
        'a': ('href', 'title', 'target', 'rel'),  # Added 'rel' attribute for anchor tags
        'span': ('style',),
    },
    'empty': {'hr', 'br'},
    'separate': {'a', 'p', 'li'},
    'whitespace': {' ', '\t', '\n', '\r', '\f'},  # Define explicit whitespace characters
    'keep_typographic_whitespace': False,
    'add_nofollow': True,
    'autolink': False,
    'sanitize_href': lambda href: href if re.match(r'^(https?|mailto):', href) else '',
})

# Regular expressions for validation
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$')
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
    
    # First use bleach to clean the HTML
    cleaned = bleach.clean(
        html_content,
        tags=sanitizer.tags,
        attributes=sanitizer.attributes,
        strip=True
    )
    
    # Then use html-sanitizer for additional cleaning
    return sanitizer.sanitize(cleaned)

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
        str: Sanitized email
        
    Raises:
        ValidationError: If email is invalid
    """
    if not email:
        raise ValidationError('Email is required')
    
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
    Validate password strength.
    
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
    
    if not PASSWORD_REGEX.match(password):
        raise ValidationError('Password must contain at least one letter and one number')
    
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

# Pydantic models for request validation

class RegisterSchema(BaseModel):
    """Schema for user registration data validation."""
    username: constr(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: constr(min_length=8, max_length=100)
    timezone: str = 'UTC'
    
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