"""Compatibility entry point for the migrated WaterMist application.

Use ``python run.py`` for the Flask application and daily scheduler.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.services.game_service import GameService  # noqa: E402


def jalankan_pipeline(limit=None):
    app = create_app(start_scheduler=False)
    with app.app_context():
        return GameService().sync_recently_released(limit=limit)


def main():
    parser = argparse.ArgumentParser(description="WaterMist Steam release collector")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test-scrape", action="store_true", help="ambil maksimal 5 game")
    mode.add_argument("--once", action="store_true", help="jalankan sinkronisasi sekali")
    mode.add_argument("--schedule", action="store_true", help="jalankan Flask dan scheduler")
    args = parser.parse_args()

    if args.schedule:
        app = create_app(start_scheduler=True)
        app.run(debug=False, use_reloader=False)
    else:
        print(jalankan_pipeline(limit=5 if not args.once else None))


if __name__ == "__main__":
    main()
