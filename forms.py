from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[Optional()])
    category = StringField('Category', validators=[Optional()])
    copies = IntegerField('Available Copies', default=1, validators=[NumberRange(min=0)])
    cover_url = StringField('Cover URL', validators=[Optional(), Length(max=500)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save')

class ImportForm(FlaskForm):
    file = FileField('JSON file')
    submit = SubmitField('Upload')
