from validators import BaseForm, RegisterSchema, LoginSchema
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegistrationForm(BaseForm):
    pydantic_model = RegisterSchema
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField('Email', validators=[Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    timezone = StringField('Timezone', validators=[DataRequired()])

class LoginForm(BaseForm):
    pydantic_model = LoginSchema
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class PasswordChangeForm(BaseForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])

class EmailChangeForm(BaseForm):
    password = PasswordField('Current Password', validators=[DataRequired()])
    new_email = StringField('New Email Address', validators=[DataRequired(), Email()])
    confirm_new_email = StringField('Confirm New Email', validators=[DataRequired(), EqualTo('new_email')])

class AddEmailForm(BaseForm):
    password = PasswordField('Current Password', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])

class RequestResetForm(BaseForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(BaseForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

