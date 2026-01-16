from flask import current_app, g

from app.db import DBConfig, get_connection


def get_db():
    if "db" not in g:
        cfg = DBConfig(
            host=current_app.config["DB_HOST"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            port=current_app.config["DB_PORT"],
        )
        g.db = get_connection(cfg)
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
