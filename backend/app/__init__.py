import os
from datetime import timedelta

from flask import Flask

from .routes.admin import admin_bp
from .routes.auth import auth_bp
from .routes.products import products_bp
from .routes.seller import seller_bp
from .utils.db import close_db, init_db
from .utils.security import (
    check_csrf,
    format_review_comment,
    generate_csrf_token,
    get_secret_key,
    make_session_permanent,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.dirname(BASE_DIR)
TEMPLATE_DIR = os.path.join(WORKSPACE_DIR, "frontend", "templates")
STATIC_DIR = os.path.join(WORKSPACE_DIR, "frontend", "static")


def register_endpoint_aliases(app):
    """keep old endpoint names working even though routes now live in blueprints"""
    endpoint_aliases = {
        "auth.register": "register",
        "auth.login": "login",
        "auth.logout": "logout",
        "products.index": "index",
        "products.product_detail": "product_detail",
        "products.buy_product": "buy_product",
        "products.add_review": "add_review",
        "products.account": "account",
        "seller.become_seller": "become_seller",
        "seller.seller_dashboard": "seller_dashboard",
        "seller.add_product": "add_product",
        "seller.edit_product": "edit_product",
        "admin.admin_dashboard": "admin_dashboard",
        "admin.admin_change_role": "admin_change_role",
        "admin.admin_delete_user": "admin_delete_user",
        "admin.admin_delete_product": "admin_delete_product",
    }

    for rule in app.url_map.iter_rules():
        alias = endpoint_aliases.get(rule.endpoint)
        if not alias:
            continue

        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        app.add_url_rule(
            rule.rule,
            endpoint=alias,
            view_func=app.view_functions[rule.endpoint],
            defaults=rule.defaults,
            methods=methods,
        )


def create_app():
    app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

    app.config["SECRET_KEY"] = get_secret_key(BASE_DIR)
    app.config["DATABASE"] = os.path.join(BASE_DIR, "database.db")
    app.config["BASE_DIR"] = BASE_DIR
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.globals["format_review_comment"] = format_review_comment

    app.before_request(check_csrf)
    app.before_request(make_session_permanent)
    app.teardown_appcontext(close_db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)
    register_endpoint_aliases(app)

    with app.app_context():
        init_db()

    return app


app = create_app()
