from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .forms import LoginForm
from .models import AppUser


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = AppUser.query.filter_by(login_name=form.login_name.data.strip().lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.dashboard"))

        flash("Invalid login name or password, or the account is inactive.", "danger")

    return render_template("login.html", form=form, user_count=AppUser.query.count())


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
