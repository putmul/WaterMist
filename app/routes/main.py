from flask import Blueprint, flash, redirect, render_template, url_for

from app.services.deal_service import DealService
from app.services.game_service import GameService

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@main_bp.post("/sync/deals")
def sync_deals():
    """Run a manual deals sync from the prototype dashboard."""
    result = DealService().sync_daily()
    status = result.get("status", "failed")
    if status == "success":
        category = "success"
        message = (
            "Scraping selesai: "
            f"{result.get('records_saved', 0)} deal berhasil disimpan."
        )
    elif status == "partial":
        category = "warning"
        message = (
            "Scraping selesai sebagian: "
            f"{result.get('records_saved', 0)} deal disimpan. "
            "Periksa log untuk sumber yang gagal."
        )
    else:
        category = "error"
        message = "Scraping gagal. Periksa konfigurasi dan log aplikasi."
    flash(message, category)
    return redirect(url_for("main.dashboard"))


@main_bp.post("/sync/releases")
def sync_releases():
    """Run a manual Recently Released sync from the dashboard."""
    result = GameService().sync_recently_released()
    status = result.get("status", "failed")
    if status == "success":
        flash(
            "Scraping new releases selesai: "
            f"{result.get('records_saved', 0)} game berhasil disimpan "
            f"dari {result.get('records_fetched', 0)} hasil.",
            "success",
        )
    elif status == "partial":
        flash(
            "Scraping new releases selesai sebagian: "
            f"{result.get('records_saved', 0)} game berhasil disimpan "
            f"dari {result.get('records_fetched', 0)} hasil. Periksa log aplikasi.",
            "warning",
        )
    else:
        error = (result.get("errors") or [None])[0]
        suffix = f" ({error[:180]})" if error else ""
        flash(f"Scraping new releases gagal{suffix}. Periksa log aplikasi.", "error")
    return redirect(url_for("main.dashboard"))


@main_bp.get("/health")
def health():
    return {"status": "ok", "service": "watermist"}
