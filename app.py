import logging
from flask import Flask, session, request, jsonify, render_template
from flask_cors import CORS
from db import init_db
from auth import auth_bp
from analysis import analysis_bp
from api import api_bp
from main import main_bp
from config import Config
from i18n import i18n


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    init_db()
    i18n.init_app(app)

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("auth.html", mode="login", error=i18n.translate("page_not_found")), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template("auth.html", mode="login", error=i18n.translate("server_error")), 500

    @app.after_request
    def set_default_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.context_processor
    def inject_globals():
        lang = session.get('lang', 'en')
        return {
            "username": session.get('username'),
            "user_id": session.get('user_id'),
            "current_lang": lang,
            "html_lang": lang
        }

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=Config.FLASK_DEBUG,
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT
    )
