from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    timezone = db.Column(db.String(50), default='UTC')  # User's timezone

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    journal_entries = db.relationship('JournalEntry', backref='author', lazy='dynamic')
    exercise_logs = db.relationship('ExerciseLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password hash."""
        return check_password_hash(self.password_hash, password)
    
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
    
    # Relationship
    guided_responses = db.relationship('GuidedResponse', backref='journal_entry', lazy='dynamic', cascade='all, delete-orphan')
    
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


class QuestionManager:
    """Class to manage guided journal questions."""
    
    @staticmethod
    def get_questions():
        """Get all guided journal questions.
        
        Returns:
            list: List of question dictionaries.
        """
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
