"""Steam Web API linking and library synchronization."""

import re
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import Game, User, UserOwnedGame, UserPreference, UserSteamProfile
from app.services.game_enrichment_service import GameEnrichmentService
from app.services.preference_service import PreferenceProfileService
from app.utils.time import local_now


STEAM_ID_PATTERN = re.compile(r"^\d{17}$")
VANITY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class SteamServiceError(Exception):
    """Expected error that can be shown as a safe user-facing message."""


class SteamProfilePrivateError(SteamServiceError):
    pass


class SteamService:
    def __init__(self, http_client=None, enrichment_service=None):
        self.http = http_client or requests.Session()
        self.enrichment_service = enrichment_service or GameEnrichmentService()

    def link_profile(self, user, profile_input):
        steam_id = self.resolve_steam_id(profile_input)
        profile = UserSteamProfile.query.filter_by(user_id=user.id).one_or_none()
        if profile is None:
            profile = UserSteamProfile(user_id=user.id, steam_id=steam_id)
            db.session.add(profile)
        profile.steam_id = steam_id
        profile.profile_url = f"https://steamcommunity.com/profiles/{steam_id}"
        profile.sync_status = "pending"
        profile.last_sync_error = None
        db.session.flush()

        try:
            records = self.fetch_owned_games(steam_id)
            app_ids = self._save_owned_games(user.id, records)
            enrichment = self.enrichment_service.enrich_app_ids(app_ids)
        except SteamProfilePrivateError as exc:
            profile.visibility_status = "private"
            profile.sync_status = "failed"
            profile.last_sync_error = str(exc)
            user.preference_mode = "quiz"
            db.session.commit()
            raise
        except Exception as exc:
            profile.sync_status = "failed"
            profile.last_sync_error = str(exc)[:1000]
            db.session.commit()
            raise SteamServiceError("Library Steam tidak dapat disinkronkan saat ini.") from exc

        profile.visibility_status = "public"
        profile.sync_status = "success"
        profile.last_synced_at = local_now()
        profile.last_sync_error = None
        user.preference_mode = "steam"
        user.onboarding_status = "steam_connected"
        PreferenceProfileService().rebuild_steam_preferences(user.id)
        db.session.commit()
        profile.last_sync_error = self._enrichment_message(enrichment)
        db.session.commit()
        return profile

    def resolve_steam_id(self, value):
        value = (value or "").strip()
        if STEAM_ID_PATTERN.fullmatch(value):
            return value

        match = re.search(r"/profiles/(\d{17})(?:/|$)", value)
        if match:
            return match.group(1)

        vanity_match = re.search(r"/id/([^/?#]+)(?:/|$)", value)
        vanity = vanity_match.group(1) if vanity_match else value
        if not VANITY_PATTERN.fullmatch(vanity):
            raise SteamServiceError("Steam ID atau Profile URL tidak valid.")
        if not current_app.config.get("STEAM_API_KEY"):
            raise SteamServiceError("STEAM_API_KEY belum dikonfigurasi.")

        payload = self._get_json(
            "/ISteamUser/ResolveVanityURL/v0001/",
            {"key": current_app.config["STEAM_API_KEY"], "vanityurl": vanity},
        )
        response = payload.get("response", {})
        steam_id = str(response.get("steamid", ""))
        if response.get("success") != 1 or not STEAM_ID_PATTERN.fullmatch(steam_id):
            raise SteamServiceError("Steam Profile tidak ditemukan.")
        return steam_id

    def fetch_owned_games(self, steam_id):
        if not current_app.config.get("STEAM_API_KEY"):
            raise SteamServiceError("STEAM_API_KEY belum dikonfigurasi.")
        payload = self._get_json(
            "/IPlayerService/GetOwnedGames/v0001/",
            {
                "key": current_app.config["STEAM_API_KEY"],
                "steamid": steam_id,
                "format": "json",
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
        )
        response = payload.get("response", {})
        if "games" not in response:
            raise SteamProfilePrivateError(
                "Library Steam privat atau tidak tersedia. Gunakan quiz preferensi."
            )
        return response.get("games", [])

    def sync_user(self, user):
        profile = UserSteamProfile.query.filter_by(user_id=user.id).one_or_none()
        if profile is None:
            raise SteamServiceError("Akun Steam belum ditautkan.")
        try:
            records = self.fetch_owned_games(profile.steam_id)
        except SteamProfilePrivateError as exc:
            profile.visibility_status = "private"
            profile.sync_status = "failed"
            profile.last_sync_error = str(exc)
            user.preference_mode = "quiz"
            db.session.commit()
            raise
        except Exception as exc:
            profile.sync_status = "failed"
            profile.last_sync_error = str(exc)[:1000]
            db.session.commit()
            raise SteamServiceError("Library Steam tidak dapat disinkronkan saat ini.") from exc
        app_ids = self._save_owned_games(user.id, records)
        enrichment = self.enrichment_service.enrich_app_ids(app_ids)
        profile.visibility_status = "public"
        profile.sync_status = "success"
        profile.last_synced_at = local_now()
        profile.last_sync_error = None
        user.preference_mode = "steam"
        PreferenceProfileService().rebuild_steam_preferences(user.id)
        db.session.commit()
        profile.last_sync_error = self._enrichment_message(enrichment)
        db.session.commit()
        return profile

    def sync_all_users(self):
        """Refresh linked libraries without allowing one private profile to stop the job."""
        synced = 0
        failed = 0
        for profile in UserSteamProfile.query.filter_by(disconnected_at=None).all():
            user = db.session.get(User, profile.user_id)
            if user is None or user.status != "active":
                continue
            try:
                self.sync_user(user)
                synced += 1
            except SteamServiceError:
                failed += 1
        return {"synced": synced, "failed": failed}

    def disconnect(self, user):
        UserOwnedGame.query.filter_by(user_id=user.id).delete()
        UserPreference.query.filter_by(user_id=user.id, source="steam").delete()
        profile = UserSteamProfile.query.filter_by(user_id=user.id).one_or_none()
        if profile is not None:
            db.session.delete(profile)
        user.preference_mode = "quiz"
        user.onboarding_status = "quiz_completed" if user.quiz_answers else "not_started"
        db.session.commit()

    def _save_owned_games(self, user_id, records):
        UserOwnedGame.query.filter_by(user_id=user_id).delete()
        app_ids = []
        for record in records:
            app_id = str(record.get("appid", ""))
            if not app_id.isdigit():
                continue
            app_ids.append(app_id)
            game = Game.query.filter_by(steam_app_id=app_id).one_or_none()
            if game is None:
                game = Game(
                    name=(record.get("name") or f"Steam App {app_id}").strip(),
                    steam_app_id=app_id,
                )
                db.session.add(game)
                db.session.flush()
            try:
                playtime = max(0, int(record.get("playtime_forever", 0) or 0))
                recent_playtime = max(0, int(record.get("playtime_2weeks", 0) or 0))
            except (TypeError, ValueError):
                playtime = 0
                recent_playtime = 0
            db.session.add(
                UserOwnedGame(
                    user_id=user_id,
                    game_id=game.id if game else None,
                    steam_app_id=app_id,
                    playtime_minutes=playtime,
                    recent_playtime_minutes=recent_playtime,
                    last_played_at=self._parse_last_played(record.get("rtime_last_played")),
                    synced_at=local_now(),
                )
            )
        db.session.flush()
        return app_ids

    @staticmethod
    def _enrichment_message(stats):
        if not stats or not stats.get("failed"):
            return None
        return (
            f"Enrichment metadata sebagian gagal: {stats['failed']} dari "
            f"{stats['requested']} game."
        )

    def _get_json(self, path, params):
        url = current_app.config["STEAM_API_BASE_URL"].rstrip("/") + path
        response = self.http.get(
            url, params=params, timeout=current_app.config["REQUEST_TIMEOUT_SECONDS"]
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_last_played(value):
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError, OSError):
            return None


__all__ = ["SteamService", "SteamServiceError", "SteamProfilePrivateError"]
