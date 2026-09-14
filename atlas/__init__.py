from flask import Flask
from flask_wtf.csrf import CSRFProtect

from config import Config

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    csrf.init_app(app)

    from .db import init_db
    init_db(app)

    from .routes import register_blueprints
    register_blueprints(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    from flask import render_template

    @app.errorhandler(404)
    def _404(e):
        return render_template("errors/404.html"), 404

    return app
