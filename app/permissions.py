from __future__ import annotations

from flask import abort
from flask_login import current_user


def require_admin() -> None:
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def require_owner_or_admin(owner_user_id: int) -> None:
    if not current_user.is_authenticated:
        abort(403)
    if not (current_user.is_admin or current_user.id == owner_user_id):
        abort(403)
