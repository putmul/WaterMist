"""Minimal session authentication helpers for the WaterMist MVP."""

from functools import wraps

from flask import abort, session

from app.models import User


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = User.query.filter_by(id=user_id, status="active").one_or_none()
    if user is None:
        session.pop("user_id", None)
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            abort(401)
        return view(*args, **kwargs)

    return wrapped
