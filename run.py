"""WaterVapor application entry point."""

from app import create_app

app = create_app(start_scheduler=False)


if __name__ == "__main__":
    app = create_app(start_scheduler=True)
    app.run(debug=False, use_reloader=False)
