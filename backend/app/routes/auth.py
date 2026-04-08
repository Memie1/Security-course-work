import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..utils.db import get_db, log_activity
from ..utils.validators import EMAIL_RE, MIN_PASSWORD_LEN, USERNAME_RE


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # This route handles account creation and basic input checks.
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        errors = []
        if not USERNAME_RE.match(username):
            errors.append("Username must be 3-20 characters (letters, numbers, underscores).")
        if not EMAIL_RE.match(email):
            errors.append("Enter a valid email address.")
        if len(password) < MIN_PASSWORD_LEN:
            errors.append(f"Password must be at least {MIN_PASSWORD_LEN} characters.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            db.commit()
            log_activity("register", f"New account: {username}")
            flash("Account created — you can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username or email is already taken.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Login stores the user's ID and role in the session after the password is checked.
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            log_activity("login_fail", f"Failed attempt for {email}")
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True

        log_activity("login", f"{user['username']} logged in")
        flash("Logged in successfully.", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Logout clears the current session and sends the user back to the homepage.
    log_activity("logout")
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
