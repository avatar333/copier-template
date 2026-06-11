from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, Optional, Regexp

LOGIN_NAME_VALIDATOR = Regexp(
    r"^[a-z0-9._-]+$",
    message="Login name may contain lowercase letters, numbers, dots, underscores, and hyphens only.",
)


class LoginForm(FlaskForm):
    login_name = StringField("Login name", validators=[InputRequired(), Length(max=100), LOGIN_NAME_VALIDATOR])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Log in")


class UserForm(FlaskForm):
    login_name = StringField("Login name", validators=[InputRequired(), Length(max=100), LOGIN_NAME_VALIDATOR])
    first_name = StringField("First name", validators=[InputRequired(), Length(max=100)])
    last_name = StringField("Last name", validators=[InputRequired(), Length(max=100)])
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=255)])
    is_admin = BooleanField("Admin user")
    assign_only_production_pets = BooleanField("Assign ONLY Production Pets")
    assign_only_non_production_pets = BooleanField("Assign ONLY Non-Production Pets")
    is_active = BooleanField("Active user", default=True)
    production_pet_blob = HiddenField()
    non_production_pet_blob = HiddenField()
    submit = SubmitField("Save")
