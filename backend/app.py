import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.config["SECRET_KEY"] = "change-this-in-real-submission"
app.config["DATABASE"] = "database.db"


# -----------------------------
# Database helpers
# -----------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        seller_id INTEGER,
        FOREIGN KEY (seller_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    );
    """)
    db.commit()


@app.route("/init-db")
def init_db_route():
    init_db()

    db = get_db()
    existing = db.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]

    if existing == 0:
        db.execute(
            "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
            ("Wireless Headphones", "Basic demo product", 89.99)
        )
        db.execute(
            "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
            ("Oxford Shirt", "Simple clothing item", 24.99)
        )
        db.execute(
            "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
            ("Cookware Set", "Basic household product", 64.99)
        )
        db.commit()

    return "Database initialized."


# -----------------------------
# Auth helpers
# -----------------------------
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("You need to log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def role_required(required_role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("You need to log in first.")
                return redirect(url_for("login"))

            if session.get("role") != required_role:
                flash("You do not have permission to access that page.")
                return redirect(url_for("index"))

            return view(*args, **kwargs)
        return wrapped_view
    return decorator


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    return render_template("index.html", products=products)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            db.commit()
            flash("Account created. You can now log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid login details.")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        flash("Logged in successfully.")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        return "Product not found.", 404

    reviews = db.execute("""
        SELECT reviews.*, users.username
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        WHERE product_id = ?
        ORDER BY reviews.id DESC
    """, (product_id,)).fetchall()

    return render_template("product.html", product=product, reviews=reviews)


@app.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
def add_review(product_id):
    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    if not rating or not comment:
        flash("Rating and comment are required.")
        return redirect(url_for("product_detail", product_id=product_id))

    try:
        rating_value = int(rating)
    except ValueError:
        flash("Invalid rating.")
        return redirect(url_for("product_detail", product_id=product_id))

    if rating_value < 1 or rating_value > 5:
        flash("Rating must be between 1 and 5.")
        return redirect(url_for("product_detail", product_id=product_id))

    db = get_db()
    db.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
        (product_id, session["user_id"], rating_value, comment)
    )
    db.commit()

    flash("Review added.")
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/product/<int:product_id>/buy", methods=["POST"])
@login_required
def buy_product(product_id):
    quantity = request.form.get("quantity", "1").strip()

    try:
        quantity_value = int(quantity)
    except ValueError:
        flash("Invalid quantity.")
        return redirect(url_for("product_detail", product_id=product_id))

    if quantity_value < 1:
        flash("Quantity must be at least 1.")
        return redirect(url_for("product_detail", product_id=product_id))

    db = get_db()
    db.execute(
        "INSERT INTO orders (user_id, product_id, quantity) VALUES (?, ?, ?)",
        (session["user_id"], product_id, quantity_value)
    )
    db.commit()

    flash("Purchase recorded.")
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/become-seller", methods=["POST"])
@login_required
def become_seller():
    db = get_db()
    db.execute(
        "UPDATE users SET role = 'seller' WHERE id = ?",
        (session["user_id"],)
    )
    db.commit()
    session["role"] = "seller"
    flash("Your account is now a seller account.")
    return redirect(url_for("index"))


@app.route("/seller/add-product", methods=["GET", "POST"])
@role_required("seller")
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()

        if not name or not description or not price:
            flash("All fields are required.")
            return redirect(url_for("add_product"))

        try:
            price_value = float(price)
        except ValueError:
            flash("Invalid price.")
            return redirect(url_for("add_product"))

        db = get_db()
        db.execute(
            "INSERT INTO products (name, description, price, seller_id) VALUES (?, ?, ?, ?)",
            (name, description, price_value, session["user_id"])
        )
        db.commit()

        flash("Product added.")
        return redirect(url_for("index"))

    return """
    <h1>Add Product</h1>
    <form method="post">
        <input name="name" placeholder="Name"><br><br>
        <textarea name="description" placeholder="Description"></textarea><br><br>
        <input name="price" placeholder="Price"><br><br>
        <button type="submit">Add Product</button>
    </form>
    """


if __name__ == "__main__":
    app.run(debug=True)