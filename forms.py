from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class TinyMCEField(TextAreaField):
    pass

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    timezone = SelectField('Timezone', validators=[DataRequired()], choices=[])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])

class EmailChangeForm(FlaskForm):
    password = PasswordField('Current Password', validators=[DataRequired()])
    new_email = StringField('New Email Address', validators=[DataRequired(), Email()])
    confirm_new_email = StringField('Confirm New Email', validators=[DataRequired(), EqualTo('new_email')])

class AddEmailForm(FlaskForm):
    password = PasswordField('Current Password', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class QuickJournalForm(FlaskForm):
    content = TinyMCEField('Content', validators=[DataRequired(), Length(max=10000)])
    tags = StringField('Tags') # This will be handled by JS
    new_tags = StringField('New Tags') # This will be handled by JS

class GuidedJournalForm(FlaskForm):
    # Guided journal questions are dynamic, so we'll handle them in the route
    # The content field will be used for the main guided response
    content = TinyMCEField('Content', validators=[Length(max=10000)])
    tags = StringField('Tags') # This will be handled by JS
    new_tags = StringField('New Tags') # This will be handled by JS

class ReminderForm(FlaskForm):
    frequency = StringField('Frequency', validators=[DataRequired()])
    time_of_day = StringField('Time of Day') # HH:MM format
    message = StringField('Message', validators=[Length(max=255)])
    enabled = BooleanField('Enabled')