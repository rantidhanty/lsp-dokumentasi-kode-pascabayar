import os

from dotenv import load_dotenv
from flask import Flask

from .db import init_app as init_db
from .routes import register_routes


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    app.config["DB_HOST"] = os.getenv("DB_HOST", "localhost")
    app.config["DB_USER"] = os.getenv("DB_USER", "root")
    app.config["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "")
    app.config["DB_NAME"] = os.getenv("DB_NAME", "lsp_listrik")
    app.config["DB_PORT"] = int(os.getenv("DB_PORT", "3306"))

    app.config["MIDTRANS_SERVER_KEY"] = os.getenv("MIDTRANS_SERVER_KEY", "")
    app.config["MIDTRANS_CLIENT_KEY"] = os.getenv("MIDTRANS_CLIENT_KEY", "")
    app.config["MIDTRANS_IS_PRODUCTION"] = (
        os.getenv("MIDTRANS_IS_PRODUCTION", "false").lower() == "true"
    )

    @app.template_filter("rupiah")
    def format_rupiah(value) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0
        formatted = f"{amount:,.0f}".replace(",", ".")
        return f"Rp {formatted}"

    init_db(app)
    register_routes(app)
    return app
