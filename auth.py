from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, get_user_id
from i18n import i18n

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_user_id():
        return redirect(url_for('analysis.index'))
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        conn.close()
        if row and check_password_hash(row[1], password):
            session['user_id'] = row[0]
            session['username'] = username
            return redirect(url_for('analysis.index'))
        else:
            error = i18n.translate("invalid_credentials")
    return render_template("auth.html", mode="login", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if get_user_id():
        return redirect(url_for('analysis.index'))
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3:
            error = i18n.translate("username_short")
        elif len(password) < 6:
            error = i18n.translate("password_short")
        else:
            try:
                conn = get_db()
                c = conn.cursor()
                c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                          (username, generate_password_hash(password)))
                conn.commit()
                conn.close()
                flash(i18n.translate("registration_success"), 'success')
                return redirect(url_for('auth.login'))
            except Exception:
                error = i18n.translate("username_taken")
    return render_template("auth.html", mode="register", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
