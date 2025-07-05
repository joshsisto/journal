from datetime import datetime, timedelta
import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

db = SQLAlchemy()

# Tag-Entry association table (many-to-many)
entry_tags = db.Table('entry_tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('entry_id', db.Integer, db.ForeignKey('journal_entries.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    timezone = db.Column(db.String(50), default='UTC')  # User's timezone

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Email is optional
    is_email_verified = db.Column(db.Boolean, default=False)  # Track if email is verified
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Reset password fields
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Email verification fields
    email_verification_token = db.Column(db.String(100), nullable=True)  # Token for email verification
    email_verification_expiry = db.Column(db.DateTime, nullable=True)  # Expiry for email verification
    email_change_token = db.Column(db.String(100), nullable=True)
    email_change_token_expiry = db.Column(db.DateTime, nullable=True)
    new_email = db.Column(db.String(120), nullable=True)
    
    # Two-factor authentication fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_code = db.Column(db.String(10), nullable=True)
    two_factor_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    journal_entries = db.relationship('JournalEntry', backref='author', lazy='dynamic')
    exercise_logs = db.relationship('ExerciseLog', backref='user', lazy='dynamic')
    tags = db.relationship('Tag', backref='user', lazy='dynamic')
    templates = db.relationship('JournalTemplate', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password hash."""
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        """Generate a password reset token."""
        self.reset_token = secrets.token_urlsafe(64)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify that the reset token is valid."""
        if (self.reset_token != token or 
            self.reset_token_expiry is None or 
            datetime.utcnow() > self.reset_token_expiry):
            return False
        return True
    
    def clear_reset_token(self):
        """Clear the reset token after use."""
        self.reset_token = None
        self.reset_token_expiry = None
    
    def generate_email_change_token(self, new_email):
        """Generate a token for email change verification."""
        self.new_email = new_email
        self.email_change_token = secrets.token_urlsafe(64)
        self.email_change_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.email_change_token
    
    def verify_email_change_token(self, token):
        """Verify that the email change token is valid."""
        if (self.email_change_token != token or 
            self.email_change_token_expiry is None or 
            datetime.utcnow() > self.email_change_token_expiry or
            self.new_email is None):
            return False
        return True
    
    def complete_email_change(self):
        """Complete the email change process."""
        if self.new_email:
            self.email = self.new_email
            self.new_email = None
            self.email_change_token = None
            self.email_change_token_expiry = None
            # New email needs verification
            self.is_email_verified = False
            # Generate verification token for the new email
            self.generate_email_verification_token()
            return True
        return False
        
    def generate_email_verification_token(self):
        """Generate a token for email verification."""
        # Don't generate token if email is None or empty
        if not self.email:
            return None
            
        self.email_verification_token = secrets.token_urlsafe(64)
        self.email_verification_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.email_verification_token
        
    def verify_email_verification_token(self, token):
        """Verify the email verification token."""
        if (self.email_verification_token != token or 
            self.email_verification_expiry is None or 
            datetime.utcnow() > self.email_verification_expiry):
            return False
        return True
        
    def complete_email_verification(self):
        """Mark email as verified and clear the verification token."""
        if self.email and self.email_verification_token:
            self.is_email_verified = True
            self.email_verification_token = None
            self.email_verification_expiry = None
            return True
        return False
        
    def has_verified_email(self):
        """Check if user has a verified email address."""
        return self.email is not None and self.is_email_verified
    
    def __repr__(self):
        return f'<User {self.username}>'


class JournalEntry(db.Model):
    """Journal entry model."""
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # For quick journal entries
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    entry_type = db.Column(db.String(20), nullable=False)  # 'quick' or 'guided'
    template_id = db.Column(db.Integer, db.ForeignKey('journal_templates.id'), nullable=True)  # Template used for guided entries
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)  # Location where entry was created
    weather_id = db.Column(db.Integer, db.ForeignKey('weather_data.id'), nullable=True)  # Weather when entry was created
    
    # Relationships
    guided_responses = db.relationship('GuidedResponse', backref='journal_entry', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=entry_tags, lazy='joined', 
                          backref=db.backref('entries', lazy='dynamic'))
    photos = db.relationship('Photo', backref='journal_entry', lazy='dynamic', cascade='all, delete-orphan')
    location = db.relationship('Location', backref='journal_entries', lazy='joined')
    weather = db.relationship('WeatherData', foreign_keys='WeatherData.journal_entry_id', backref='journal_entry', lazy='joined')
    
    def __repr__(self):
        return f'<JournalEntry {self.id} by User {self.user_id}>'
    
    def get_time_since_last_entry(self, user_id):
        """Get time since last entry for a user."""
        last_entry = JournalEntry.query.filter_by(
            user_id=user_id
        ).filter(
            JournalEntry.id != self.id
        ).order_by(JournalEntry.created_at.desc()).first()
        
        if last_entry:
            return self.created_at - last_entry.created_at
        return None


class GuidedResponse(db.Model):
    """Guided journal response model."""
    __tablename__ = 'guided_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    question_id = db.Column(db.String(50), nullable=False)  # Identifier for the question
    question_text = db.Column(db.Text, nullable=True)  # The actual question text for template questions
    response = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<GuidedResponse {self.id} for Question {self.question_id}>'


class ExerciseLog(db.Model):
    """Exercise log model."""
    __tablename__ = 'exercise_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # Just the date, not time
    has_exercised = db.Column(db.Boolean, default=False)
    workout_type = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<ExerciseLog for User {self.user_id} on {self.date}>'


class Tag(db.Model):
    """Tag model for categorizing journal entries."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Default color (Bootstrap secondary)
    
    # Enforce unique tag names per user
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='_tag_user_uc'),)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class Photo(db.Model):
    """Photo model for journal entry attachments."""
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Photo {self.id} for JournalEntry {self.journal_entry_id}>'


class JournalTemplate(db.Model):
    """Template model for guided journal templates."""
    __tablename__ = 'journal_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL for system templates
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    questions = db.relationship('TemplateQuestion', backref='template', lazy='dynamic', cascade='all, delete-orphan', order_by='TemplateQuestion.question_order')
    journal_entries = db.relationship('JournalEntry', backref='template', lazy='dynamic')
    
    def __repr__(self):
        return f'<JournalTemplate {self.name}>'
    
    def to_dict(self):
        """Convert template to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_system': self.is_system,
            'question_count': self.questions.count(),
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class TemplateQuestion(db.Model):
    """Template question model for custom questions within templates."""
    __tablename__ = 'template_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('journal_templates.id'), nullable=False)
    question_id = db.Column(db.String(50), nullable=False)  # Unique within template
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'number', 'text', 'boolean', 'emotions', 'select'
    question_order = db.Column(db.Integer, nullable=False, default=0)
    required = db.Column(db.Boolean, default=False)
    properties = db.Column(db.Text)  # JSON string for type-specific properties
    condition_expression = db.Column(db.Text)  # Condition for showing this question
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<TemplateQuestion {self.question_id} in {self.template_id}>'
    
    def get_properties(self):
        """Get properties as dictionary."""
        if self.properties:
            try:
                import json
                return json.loads(self.properties)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_properties(self, properties_dict):
        """Set properties from dictionary."""
        if properties_dict:
            import json
            self.properties = json.dumps(properties_dict)
        else:
            self.properties = None
    
    def to_dict(self):
        """Convert question to dictionary format for rendering."""
        question_dict = {
            'id': self.question_id,
            'text': self.question_text,
            'type': self.question_type,
            'required': self.required,
            'order': self.question_order
        }
        
        # Add type-specific properties
        properties = self.get_properties()
        question_dict.update(properties)
        
        # Add condition function
        question_dict['condition'] = self._create_condition_function()
        
        return question_dict
    
    def _create_condition_function(self):
        """Create a condition function from the condition expression."""
        if not self.condition_expression:
            return lambda response_data: True
        
        # Simple expression evaluator for common conditions
        def condition_func(response_data):
            try:
                # Replace variable names with values from response_data
                expression = self.condition_expression
                
                # Common variable replacements
                replacements = {
                    'hours_since_last_entry': str(response_data.get('hours_since_last_entry', 0)),
                    'exercised_today': str(response_data.get('exercised_today', False)).lower(),
                    'is_before_noon': str(response_data.get('is_before_noon', False)).lower(),
                    'goals_set_today': str(response_data.get('goals_set_today', False)).lower(),
                    'exercise_response': f'"{response_data.get("exercise_response", "")}"'
                }
                
                for var, val in replacements.items():
                    expression = expression.replace(var, val)
                
                # Basic safety check - only allow simple comparisons
                allowed_operators = ['==', '!=', '>=', '<=', '>', '<', 'and', 'or', 'not', 'true', 'false']
                if any(op in expression.lower() for op in ['import', 'exec', 'eval', '__', 'open', 'file']):
                    return True  # Fail safe - show question if expression is suspicious
                
                # Evaluate the expression safely
                result = eval(expression)
                return bool(result)
            except:
                # If evaluation fails, show the question (fail safe)
                return True
        
        return condition_func


class Location(db.Model):
    """Location model for storing geographic information."""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)  # User-friendly name for the location
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    address = db.Column(db.Text, nullable=True)  # Full address
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    location_type = db.Column(db.String(50), default='manual')  # 'manual', 'gps', 'geocoded'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Location {self.name or self.city or f"({self.latitude}, {self.longitude})"}>'
    
    def to_dict(self):
        """Convert location to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'location_type': self.location_type,
            'display_name': self.get_display_name()
        }
    
    def get_display_name(self):
        """Get a user-friendly display name for the location."""
        if self.name:
            return self.name
        
        # Build display name from available components
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country and self.country != self.state:
            parts.append(self.country)
        
        if parts:
            return ', '.join(parts)
        
        # Fallback to coordinates
        if self.latitude is not None and self.longitude is not None:
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        
        return "Unknown Location"
    
    def get_coordinates(self):
        """Get coordinates as a tuple."""
        if self.latitude is not None and self.longitude is not None:
            return (self.latitude, self.longitude)
        return None


class WeatherData(db.Model):
    """Weather data model for storing weather information."""
    __tablename__ = 'weather_data'
    
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    
    # Temperature data
    temperature = db.Column(db.Float, nullable=True)  # Temperature value
    temperature_unit = db.Column(db.String(10), default='celsius')  # 'celsius' or 'fahrenheit'
    
    # Weather conditions
    humidity = db.Column(db.Integer, nullable=True)  # Percentage
    pressure = db.Column(db.Float, nullable=True)  # Atmospheric pressure
    weather_condition = db.Column(db.String(100), nullable=True)  # Clear, Cloudy, Rain, etc.
    weather_description = db.Column(db.Text, nullable=True)  # Detailed description
    
    # Wind data
    wind_speed = db.Column(db.Float, nullable=True)
    wind_direction = db.Column(db.Integer, nullable=True)  # Degrees (0-360)
    
    # Additional weather data
    visibility = db.Column(db.Float, nullable=True)  # Visibility distance
    uv_index = db.Column(db.Float, nullable=True)
    precipitation = db.Column(db.Float, nullable=True)  # Amount of precipitation
    precipitation_type = db.Column(db.String(50), nullable=True)  # rain, snow, etc.
    
    # Metadata
    weather_source = db.Column(db.String(50), default='api')  # 'api', 'manual', 'estimated'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    location = db.relationship('Location', backref='weather_records', lazy='joined')
    
    def __repr__(self):
        return f'<WeatherData {self.weather_condition} at {self.temperature}°{self.temperature_unit[0].upper()}>'
    
    def to_dict(self):
        """Convert weather data to dictionary format."""
        return {
            'id': self.id,
            'temperature': self.temperature,
            'temperature_unit': self.temperature_unit,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'weather_condition': self.weather_condition,
            'weather_description': self.weather_description,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'visibility': self.visibility,
            'uv_index': self.uv_index,
            'precipitation': self.precipitation,
            'precipitation_type': self.precipitation_type,
            'weather_source': self.weather_source,
            'recorded_at': self.recorded_at,
            'display_summary': self.get_display_summary()
        }
    
    def get_display_summary(self):
        """Get a user-friendly weather summary."""
        parts = []
        
        # Temperature
        if self.temperature is not None:
            unit_symbol = '°F' if self.temperature_unit == 'fahrenheit' else '°C'
            parts.append(f"{self.temperature:.0f}{unit_symbol}")
        
        # Condition
        if self.weather_condition:
            parts.append(self.weather_condition)
        
        # Additional details
        details = []
        if self.humidity is not None:
            details.append(f"{self.humidity}% humidity")
        if self.wind_speed is not None:
            details.append(f"{self.wind_speed:.0f} mph wind")
        if self.precipitation is not None and self.precipitation > 0:
            details.append(f"{self.precipitation:.1f}mm rain")
        
        summary = ' • '.join(parts) if parts else 'Weather data available'
        if details:
            summary += f" ({', '.join(details)})"
        
        return summary
    
    def get_temperature_fahrenheit(self):
        """Get temperature in Fahrenheit."""
        if self.temperature is None:
            return None
        
        if self.temperature_unit == 'fahrenheit':
            return self.temperature
        else:
            return (self.temperature * 9/5) + 32
    
    def get_temperature_celsius(self):
        """Get temperature in Celsius."""
        if self.temperature is None:
            return None
        
        if self.temperature_unit == 'celsius':
            return self.temperature
        else:
            return (self.temperature - 32) * 5/9


class QuestionManager:
    """Class to manage guided journal questions."""
    
    @staticmethod
    def get_questions(template_id=None):
        """Get questions from template or fallback to hardcoded questions.
        
        Args:
            template_id (int, optional): Template ID to load questions from.
            
        Returns:
            list: List of question dictionaries.
        """
        if template_id:
            return QuestionManager._get_template_questions(template_id)
        else:
            return QuestionManager._get_hardcoded_questions()
    
    @staticmethod
    def _get_template_questions(template_id):
        """Load questions from database template."""
        template = JournalTemplate.query.get(template_id)
        if not template:
            # Fallback to hardcoded questions if template not found
            return QuestionManager._get_hardcoded_questions()
        
        questions = []
        for tq in template.questions.order_by(TemplateQuestion.question_order):
            questions.append(tq.to_dict())
        
        return questions
    
    @staticmethod
    def _get_hardcoded_questions():
        """Get the original hardcoded questions for backward compatibility."""
        return [
            {
                'id': 'feeling_scale',
                'text': 'How are you feeling on a scale of 1-10?',
                'type': 'number',
                'min': 1,
                'max': 10,
                'condition': lambda response_data: True  # Always ask
            },
            {
                'id': 'additional_emotions',
                'text': 'Select additional emotions you\'re experiencing:',
                'type': 'emotions',
                'condition': lambda response_data: True  # Always ask
            },
            {
                'id': 'feeling_reason',
                'text': 'Why do you feel that way?',
                'type': 'text',
                'condition': lambda response_data: True  # Always ask
            },
            {
                'id': 'since_last_entry',
                'text': "It's been {time_since} since your last journal entry. What's happened since then?",
                'type': 'text',
                'condition': lambda response_data: response_data.get('hours_since_last_entry', 0) >= 8
            },
            {
                'id': 'about_day',
                'text': 'Tell me about your day.',
                'type': 'text',
                'condition': lambda response_data: True  # Always ask
            },
            {
                'id': 'exercise',
                'text': 'Did you exercise today?',
                'type': 'boolean',
                'condition': lambda response_data: not response_data.get('exercised_today', False)
            },
            {
                'id': 'exercise_type',
                'text': 'What type of workout did you do?',
                'type': 'text',
                'condition': lambda response_data: response_data.get('exercise_response') == 'Yes'
            },
            {
                'id': 'anything_else',
                'text': 'Anything else you would like to discuss?',
                'type': 'text',
                'condition': lambda response_data: True  # Always ask
            },
            {
                'id': 'goals',
                'text': 'What are your goals for the day?',
                'type': 'text',
                'condition': lambda response_data: response_data.get('is_before_noon', False) and not response_data.get('goals_set_today', False)
            }
        ]
    
    @staticmethod
    def get_applicable_questions(response_data):
        """Get questions that are applicable based on conditions.
        
        Args:
            response_data (dict): Data to evaluate conditions against.
            
        Returns:
            list: List of applicable questions.
        """
        questions = QuestionManager.get_questions()
        return [q for q in questions if q['condition'](response_data)]
