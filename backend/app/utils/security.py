import os
import re
import secrets
from functools import wraps

from flask import abort, redirect, session, url_for
from markupsafe import Markup, escape


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def get_secret_key(base_dir):
    # The secret key is loaded from env first, then a local file for development use.
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    secret_file = os.path.join(base_dir, ".flask_secret_key")
    if os.path.exists(secret_file):
        with open(secret_file, "r", encoding="utf-8") as file_handle:
            return file_handle.read().strip()

    generated_key = secrets.token_hex(32)
    with open(secret_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(generated_key)
    return generated_key


def get_demo_admin_password(base_dir):
    env_password = os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if env_password:
        return env_password

    password_file = os.path.join(base_dir, ".demo_admin_password")
    if os.path.exists(password_file):
        with open(password_file, "r", encoding="utf-8") as file_handle:
            return file_handle.read().strip()

    generated_password = secrets.token_urlsafe(12)
    with open(password_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(generated_password)
    return generated_password


def generate_csrf_token():
    # Every session gets a token that forms must send back on POST requests.
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def check_csrf():
    if session is None:
        return
    from flask import request

    if request.method == "POST":
        token = session.get("_csrf_token")
        if not token or token != request.form.get("_csrf_token"):
            abort(403)


def make_session_permanent():
    session.permanent = True


def login_required(view):
    # This decorator stops anonymous users from reaching protected routes.
    @wraps(view)
    def wrapped(*args, **kwargs):
        from flask import flash

        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    # This decorator checks that the logged-in user has the right role.
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            from flask import flash

            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You don't have permission to view that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def apply_inline_formatting(text):
    safe_text = str(escape(text))
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_text)
    safe_text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe_text)
    return safe_text


def format_review_comment(comment):
    # Review formatting is limited on purpose so users cannot inject unsafe HTML.
    blocks = []
    bullet_items = []

    for raw_line in comment.splitlines():
        line = raw_line.strip()

        if not line:
            if bullet_items:
                blocks.append(f"<ul>{''.join(bullet_items)}</ul>")
                bullet_items = []
            continue

        if line.startswith("- "):
            bullet_items.append(f"<li>{apply_inline_formatting(line[2:].strip())}</li>")
            continue

        if bullet_items:
            blocks.append(f"<ul>{''.join(bullet_items)}</ul>")
            bullet_items = []

        blocks.append(f"<p>{apply_inline_formatting(line)}</p>")

    if bullet_items:
        blocks.append(f"<ul>{''.join(bullet_items)}</ul>")

    return Markup("".join(blocks))
