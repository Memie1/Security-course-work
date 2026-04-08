import os
import sqlite3

from flask import abort, current_app, g, request, session
from werkzeug.security import generate_password_hash

from .security import get_demo_admin_password


PRODUCT_BY_ID_QUERY = "SELECT * FROM products WHERE id = ?"


def get_db():
    # A single database connection is reused for the current request.
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    # The database is created and seeded here if it does not already exist.
    db = get_db()
    db.executescript(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        seller_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        image_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT NOT NULL,
        detail TEXT,
        product_id INTEGER,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    )
    db.commit()

    admin = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()
    if not admin:
        admin_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
        admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@abc.com")
        admin_password = get_demo_admin_password(current_app.config["BASE_DIR"])
        db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (
                admin_username,
                admin_email,
                generate_password_hash(admin_password),
                "admin",
            ),
        )

    count = db.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        demo_products = [
            ("Wireless Headphones", "Comfortable over-ear headphones with noise reduction.", 89.99, "Electronics"),
            ("Oxford Shirt", "Simple slim-fit shirt for casual or smart wear.", 24.99, "Clothing"),
            ("Cookware Set", "Durable stainless-steel set for everyday cooking.", 64.99, "Household"),
            ("4K Smart TV", "43-inch smart TV with streaming apps.", 319.99, "Electronics"),
            ("Running Trainers", "Lightweight trainers for gym and daily wear.", 54.99, "Clothing"),
            ("Cordless Vacuum", "Cordless vacuum cleaner with strong suction.", 119.99, "Household"),
            ("Bluetooth Speaker", "Portable waterproof speaker.", 39.99, "Electronics"),
            ("Storage Basket Set", "Minimal baskets for organising rooms.", 22.99, "Household"),
        ]
        for name, description, price, category in demo_products:
            db.execute(
                "INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)",
                (name, description, price, category),
            )

    db.commit()


def log_activity(event_type, detail=None, product_id=None):
    # This helper stores a simple audit trail for important actions.
    db = get_db()
    db.execute(
        """
        INSERT INTO activity_logs (user_id, event_type, detail, product_id, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session.get("user_id"),
            event_type,
            detail,
            product_id,
            request.remote_addr,
            request.headers.get("User-Agent", "")[:256],
        ),
    )
    db.commit()


def get_product_or_404(product_id):
    # This keeps product lookup logic in one place.
    product = get_db().execute(PRODUCT_BY_ID_QUERY, (product_id,)).fetchone()
    if not product:
        abort(404)
    return product
