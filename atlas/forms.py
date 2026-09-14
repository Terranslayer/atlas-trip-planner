import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def password_strength(_, field):
    pw = field.data or ""
    if len(pw) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"[0-9]", pw):
        raise ValidationError("Password must include at least one letter and one digit.")


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Regexp(USERNAME_RE, message="3 to 30 chars: letters, digits, underscore only."),
        ],
    )
    password = PasswordField("Password", validators=[DataRequired(), password_strength])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=1, max=30)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")
