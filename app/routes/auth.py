"""Registration, login, and preference onboarding routes."""

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.auth import current_user, login_required
from app.extensions import db
from app.models import User, UserPreference, UserQuizAnswer
from app.recommendation.normalization import normalize_feature_key
from app.services.recommendation_service import RecommendationService
from app.services.steam_service import SteamProfilePrivateError, SteamService, SteamServiceError
from app.utils.time import local_now


log = logging.getLogger(__name__)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("recommendations.recommendations"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or "@" not in email or len(password) < 8:
            flash("Email valid dan password minimal 8 karakter diperlukan.", "error")
            return render_template("register.html"), 400
        if User.query.filter_by(email=email).first() is not None:
            flash("Email sudah terdaftar.", "error")
            return render_template("register.html"), 409
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return redirect(url_for("onboarding.quiz"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email, status="active").one_or_none()
        if user is None or not user.check_password(request.form.get("password", "")):
            flash("Email atau password salah.", "error")
            return render_template("login.html"), 401
        user.last_login_at = local_now()
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return redirect(url_for("recommendations.recommendations"))
    return render_template("login.html")


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.dashboard"))


@auth_bp.post("/steam/connect")
@login_required
def connect_steam():
    user = current_user()
    try:
        SteamService().link_profile(user, request.form.get("steam_profile", ""))
    except SteamProfilePrivateError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("onboarding.quiz"))
    except SteamServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("recommendations.recommendations"))
    try:
        RecommendationService().generate_for_user(user)
    except Exception:
        # Steam linking is already committed. A recommendation failure should
        # not make a successful Steam connection look like a failed one.
        db.session.rollback()
        log.exception("Recommendation awal gagal setelah Steam terhubung untuk user %s", user.id)
        flash(
            "Steam berhasil ditautkan. Recommendation akan diperbarui pada sinkronisasi berikutnya.",
            "warning",
        )
    else:
        flash(
            "Steam berhasil ditautkan dan recommendation langsung diperbarui.",
            "success",
        )
    return redirect(url_for("recommendations.recommendations"))


@auth_bp.post("/steam/disconnect")
@login_required
def disconnect_steam():
    SteamService().disconnect(current_user())
    flash("Akun Steam dan data library berhasil dihapus dari WaterMist.", "success")
    return redirect(url_for("onboarding.quiz"))


@onboarding_bp.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    user = current_user()
    if request.method == "POST":
        genres = _values("genres")
        tags = _values("tags")
        if not genres and not tags:
            flash("Pilih minimal satu genre atau tag.", "error")
            return render_template("onboarding/quiz.html"), 400

        UserQuizAnswer.query.filter_by(user_id=user.id).delete()
        UserPreference.query.filter_by(user_id=user.id, source="quiz").delete()
        answers = {
            "genres": ",".join(normalize_feature_key(value) for value in genres),
            "tags": ",".join(normalize_feature_key(value) for value in tags),
        }
        for question_key, value in answers.items():
            if value:
                db.session.add(
                    UserQuizAnswer(
                        user_id=user.id, question_key=question_key, answer_value=value
                    )
                )
        for value in genres:
            db.session.add(
                UserPreference(
                    user_id=user.id,
                    feature_type="genre",
                    feature_key=normalize_feature_key(value),
                    preference_score=1.0,
                    source="quiz",
                    confidence=1.0,
                )
            )
        for value in tags:
            db.session.add(
                UserPreference(
                    user_id=user.id,
                    feature_type="tag",
                    feature_key=normalize_feature_key(value),
                    preference_score=1.0,
                    source="quiz",
                    confidence=1.0,
                )
            )
        user.preference_mode = "quiz"
        user.onboarding_status = "quiz_completed"
        db.session.commit()
        RecommendationService().generate_for_user(user)
        flash("Preferensi quiz berhasil disimpan.", "success")
        return redirect(url_for("recommendations.recommendations"))
    return render_template("onboarding/quiz.html")


def _values(field):
    values = request.form.getlist(field)
    if len(values) == 1 and "," in values[0]:
        values = values[0].split(",")
    normalized = []
    seen = set()
    for value in values:
        value = value.strip()
        key = normalize_feature_key(value)
        if key and key not in seen:
            normalized.append(value)
            seen.add(key)
    return normalized[:30]
