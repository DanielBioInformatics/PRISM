from flask import Blueprint, render_template, session, redirect, url_for
from i18n import i18n

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def index():
    lang = session.get('lang', 'en')
    return render_template("landing.html", current_lang=lang)


@main_bp.route("/landing")
def landing_redirect():
    return redirect(url_for('main.index'), 301)


@main_bp.route("/set_lang/<lang>")
def set_lang(lang):
    session['lang'] = lang
    print(f"Debug: Language set to: {lang}")
    return redirect(url_for('main.index'))
