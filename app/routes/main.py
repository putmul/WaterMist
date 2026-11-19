from flask import Blueprint, flash, redirect, render_template, url_for

from app.services.deal_service import DealService

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


@main_bp.get("/health")
def health():
    return {"status": "ok", "service": "watermist"}
