"""Registration, login, and preference onboarding routes."""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

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
        return redirect(url_for("deals.deals"))
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
    if current_user() is not None:
        return redirect(url_for("deals.deals"))
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
        return redirect(url_for("deals.deals"))
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
        # Keep accepting the previous form contract while the primary UI uses JSON.
        if not request.is_json and (request.form.getlist("genres") or request.form.getlist("tags")):
            genres, tags = _values("genres"), _values("tags")
            if not genres and not tags:
                flash("Pilih minimal satu genre atau tag.", "error")
                return render_template("quiz.html", quiz_answers={}), 400
            UserQuizAnswer.query.filter_by(user_id=user.id).delete()
            UserPreference.query.filter_by(user_id=user.id, source="quiz").delete()
            for key, values in (("genres", genres), ("tags", tags)):
                if values:
                    db.session.add(UserQuizAnswer(
                        user_id=user.id, question_key=key,
                        answer_value=",".join(normalize_feature_key(value) for value in values),
                    ))
                for value in values:
                    db.session.add(UserPreference(
                        user_id=user.id,
                        feature_type="genre" if key == "genres" else "tag",
                        feature_key=normalize_feature_key(value), preference_score=1.0,
                        source="quiz", confidence=1.0,
                    ))
            user.preference_mode = "quiz"
            user.onboarding_status = "quiz_completed"
            db.session.commit()
            RecommendationService().generate_for_user(user)
            flash("Preferensi quiz berhasil disimpan.", "success")
            return redirect(url_for("recommendations.recommendations"))
        allowed = {
            "genre": {"RPG", "Action", "Adventure", "Strategy", "Simulation", "Sports", "Racing", "Puzzle", "Indie", "Others"},
            "activity": {"Eksplorasi", "Cerita", "Pertarungan", "Strategi", "Membangun", "Teka-teki"},
            "mode": {"Single Player", "Multiplayer", "Keduanya"},
            "session": {"<1", "1-2", "2-4", ">4", "varies"},
            "budget": {"free", "<50", "50-100", "100-250", "250-500", ">500", "any"},
        }
        payload = request.get_json(silent=True) if request.is_json else request.form
        answers = {}
        for question_key, choices in allowed.items():
            raw = payload.get(question_key, []) if payload else []
            if isinstance(raw, str):
                raw = raw.split(",") if "," in raw else [raw]
            if not isinstance(raw, (list, tuple)):
                raw = []
            values = list(dict.fromkeys(
                value for value in raw if isinstance(value, str) and value in choices
            ))
            maximum = 3 if question_key in {"genre", "activity"} else 1
            if len(values) != len(raw) or len(values) > maximum:
                message = "Jawaban quiz tidak valid. Periksa kembali pilihanmu."
                if request.is_json:
                    return jsonify(error=message), 400
                flash(message, "error")
                return render_template("quiz.html", quiz_answers={}), 400
            answers[question_key] = values
        if any(not values for values in answers.values()):
            message = "Jawab semua pertanyaan sebelum menyimpan quiz."
            if request.is_json:
                return jsonify(error=message), 400
            flash(message, "error")
            return render_template("quiz.html", quiz_answers={}), 400

        UserQuizAnswer.query.filter_by(user_id=user.id).delete()
        UserPreference.query.filter_by(user_id=user.id, source="quiz").delete()
        for question_key, values in answers.items():
            db.session.add(UserQuizAnswer(
                user_id=user.id,
                question_key=question_key,
                answer_value=",".join(normalize_feature_key(value) for value in values),
            ))
        for value in answers["genre"]:
            db.session.add(UserPreference(
                user_id=user.id, feature_type="genre",
                feature_key=normalize_feature_key(value), preference_score=1.0,
                source="quiz", confidence=1.0,
            ))
        for value in answers["activity"]:
            db.session.add(UserPreference(
                user_id=user.id, feature_type="tag",
                feature_key=normalize_feature_key(value), preference_score=1.0,
                source="quiz", confidence=1.0,
            ))
        user.preference_mode = "quiz"
        user.onboarding_status = "quiz_completed"
        db.session.commit()
        try:
            RecommendationService().generate_for_user(user)
        except Exception:
            db.session.rollback()
            log.exception("Pembuatan rekomendasi gagal setelah quiz disimpan untuk user %s", user.id)
            message = "Quiz tersimpan, tetapi rekomendasi belum berhasil diperbarui."
            if request.is_json:
                return jsonify(success=True, warning=message, redirect=url_for("recommendations.recommendations")), 202
            flash(message, "warning")
            return redirect(url_for("recommendations.recommendations"))
        if request.is_json:
            return jsonify(success=True, redirect=url_for("recommendations.recommendations"))
        flash("Preferensi quiz berhasil disimpan.", "success")
        return redirect(url_for("recommendations.recommendations"))
    existing = {
        answer.question_key: answer.answer_value.split(",")
        for answer in UserQuizAnswer.query.filter_by(user_id=user.id).all()
    }
    return render_template("quiz.html", quiz_answers=existing)


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
