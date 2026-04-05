import os
import re
import sqlite3
import secrets
from datetime import timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, abort
)
from markupsafe import Markup, escape
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---- App setup ----

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)


def get_secret_key():
    """load secret key from env or keep a stable local dev key"""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".flask_secret_key")
    if os.path.exists(secret_file):
        with open(secret_file, "r", encoding="utf-8") as file_handle:
            return file_handle.read().strip()

    generated_key = secrets.token_hex(32)
    with open(secret_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(generated_key)
    return generated_key


def get_demo_admin_password():
    """keep demo admin password out of source while staying usable for marking"""
    env_password = os.environ.get("DEFAULT_ADMIN_PASSWORD")
    if env_password:
        return env_password

    password_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".demo_admin_password")
    if os.path.exists(password_file):
        with open(password_file, "r", encoding="utf-8") as file_handle:
            return file_handle.read().strip()

    generated_password = secrets.token_urlsafe(12)
    with open(password_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(generated_password)
    return generated_password


app.config["SECRET_KEY"] = get_secret_key()
app.config["DATABASE"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "database.db"
)

# session and cookie security
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max upload

# folder for review images
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
PRODUCT_BY_ID_QUERY = "SELECT * FROM products WHERE id = ?"


def allowed_file(filename):
    """check the file extension is one we allow"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---- Database helpers ----

def get_db():
    """get a database connection for the current request"""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """create tables and seed starter data if the db is empty"""
    db = get_db()
    db.executescript("""
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
    """)
    db.commit()

    # demo admin seed for marking convenience - use env vars to override
    admin = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()
    if not admin:
        admin_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
        admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@abc.com")
        admin_password = get_demo_admin_password()
        db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (
                admin_username,
                admin_email,
                generate_password_hash(admin_password),
                "admin"
            )
        )

    # seed some products so the shop isn't empty on first run
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
        for name, desc, price, cat in demo_products:
            db.execute(
                "INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)",
                (name, desc, price, cat)
            )

    db.commit()


def log_activity(event_type, detail=None, product_id=None):
    """write one row to the activity log for auditing"""
    db = get_db()
    db.execute(
        """INSERT INTO activity_logs
           (user_id, event_type, detail, product_id, ip_address, user_agent)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            session.get("user_id"),
            event_type,
            detail,
            product_id,
            request.remote_addr,
            request.headers.get("User-Agent", "")[:256],
        )
    )
    db.commit()


def apply_inline_formatting(text):
    """escape text first, then allow a tiny subset of formatting markers"""
    safe_text = str(escape(text))
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_text)
    safe_text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe_text)
    return safe_text


def format_review_comment(comment):
    """convert a limited markdown-style format into safe html"""
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


def get_product_or_404(product_id):
    """fetch one product or stop with 404"""
    product = get_db().execute(PRODUCT_BY_ID_QUERY, (product_id,)).fetchone()
    if not product:
        abort(404)
    return product


def validate_product_form(form_data):
    """collect and validate product form fields in one place"""
    name = form_data.get("name", "").strip()
    description = form_data.get("description", "").strip()
    price = form_data.get("price", "").strip()
    category = form_data.get("category", "General").strip()

    errors = []
    if not name or len(name) > 100:
        errors.append("Product name is required (max 100 characters).")
    if not description or len(description) > 2000:
        errors.append("Description is required (max 2000 characters).")

    try:
        price_value = float(price)
        if price_value <= 0 or price_value > 99999:
            errors.append("Price must be between £0.01 and £99,999.")
    except (ValueError, TypeError):
        errors.append("Enter a valid price.")
        price_value = 0

    return {
        "name": name,
        "description": description,
        "price": price_value,
        "category": category,
        "errors": errors,
    }


# ---- CSRF protection ----

def generate_csrf_token():
    """create a per-session token to protect forms against cross-site request forgery"""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


# make it available in every template as csrf_token()
app.jinja_env.globals["csrf_token"] = generate_csrf_token
app.jinja_env.globals["format_review_comment"] = format_review_comment


@app.before_request
def check_csrf():
    """reject any POST that doesn't carry the right csrf token"""
    if request.method == "POST":
        token = session.get("_csrf_token")
        if not token or token != request.form.get("_csrf_token"):
            abort(403)


@app.before_request
def make_session_permanent():
    """ensure the session timeout setting actually applies"""
    session.permanent = True


# ---- Auth decorators ----

def login_required(view):
    """redirect to login page if user isn't signed in"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """only allow users whose role is in the given list"""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You don't have permission to view that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


# ---- Validation helpers ----

USERNAME_RE = re.compile(r"^\w{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
MAX_COMMENT_LEN = 2000


# =========================================================
# Routes
# =========================================================

# -- Homepage with product listing --

@app.route("/", methods=["GET"])
def index():
    """shows all products with optional search and category filter"""
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    # build query with parameterised inputs to prevent sql injection
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY id DESC"

    products = db.execute(query, params).fetchall()
    categories = db.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()

    return render_template(
        "index.html", products=products, categories=categories,
        search=search, current_category=category
    )


# -- Single product page --

@app.route("/product/<int:product_id>", methods=["GET"])
def product_detail(product_id):
    """show one product with its reviews"""
    db = get_db()
    product = get_product_or_404(product_id)

    reviews = db.execute("""
        SELECT reviews.*, users.username
        FROM reviews JOIN users ON reviews.user_id = users.id
        WHERE reviews.product_id = ?
        ORDER BY reviews.id DESC
    """, (product_id,)).fetchall()

    # check if user has bought this (needed to allow reviews)
    has_purchased = False
    if "user_id" in session:
        order = db.execute(
            "SELECT id FROM orders WHERE user_id = ? AND product_id = ?",
            (session["user_id"], product_id)
        ).fetchone()
        has_purchased = order is not None

    log_activity("product_view", product["name"], product_id)

    return render_template(
        "product.html", product=product, reviews=reviews,
        has_purchased=has_purchased
    )


# =========================================================
# Auth routes
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # server-side validation
        errors = []
        if not USERNAME_RE.match(username):
            errors.append("Username must be 3-20 characters (letters, numbers, underscores).")
        if not EMAIL_RE.match(email):
            errors.append("Enter a valid email address.")
        if len(password) < MIN_PASSWORD_LEN:
            errors.append(f"Password must be at least {MIN_PASSWORD_LEN} characters.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("register"))

        pw_hash = generate_password_hash(password)
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, pw_hash)
            )
            db.commit()
            log_activity("register", f"New account: {username}")
            flash("Account created — you can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username or email is already taken.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            # log failed attempt, but don't reveal which field was wrong
            log_activity("login_fail", f"Failed attempt for {email}")
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        # clear session to prevent session fixation
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True

        log_activity("login", f"{user['username']} logged in")
        flash("Logged in successfully.", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    log_activity("logout")
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# =========================================================
# Customer routes
# =========================================================

@app.route("/product/<int:product_id>/buy", methods=["POST"])
@login_required
def buy_product(product_id):
    db = get_db()
    product = get_product_or_404(product_id)

    quantity = request.form.get("quantity", "1").strip()
    try:
        qty = int(quantity)
    except ValueError:
        flash("Invalid quantity.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    if qty < 1 or qty > 99:
        flash("Quantity must be between 1 and 99.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    db.execute(
        "INSERT INTO orders (user_id, product_id, quantity) VALUES (?, ?, ?)",
        (session["user_id"], product_id, qty)
    )
    db.commit()

    log_activity("purchase", f"Bought {qty}x {product['name']}", product_id)
    flash("Purchase complete!", "success")
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
def add_review(product_id):
    """submit a review - only allowed if user actually bought the product"""
    db = get_db()
    product = get_product_or_404(product_id)

    # enforce purchased-only reviews
    order = db.execute(
        "SELECT id FROM orders WHERE user_id = ? AND product_id = ?",
        (session["user_id"], product_id)
    ).fetchone()
    if not order:
        flash("You can only review products you have purchased.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    # validate rating
    try:
        rating_val = int(rating)
    except (ValueError, TypeError):
        flash("Please select a rating.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    if rating_val < 1 or rating_val > 5:
        flash("Rating must be between 1 and 5.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    # validate comment length
    if not comment or len(comment) > MAX_COMMENT_LEN:
        flash(f"Comment is required (max {MAX_COMMENT_LEN} characters).", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    # handle optional image upload
    image_filename = None
    file = request.files.get("image")
    if file and file.filename:
        if not allowed_file(file.filename):
            flash("Only png, jpg, jpeg, webp images are allowed.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        if not file.mimetype or not file.mimetype.startswith("image/"):
            flash("Uploaded file must be a real image type.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        # use secure_filename + random prefix to avoid collisions and path traversal
        safe_name = secure_filename(file.filename)
        unique_name = f"{secrets.token_hex(8)}_{safe_name}"
        file.save(os.path.join(UPLOAD_FOLDER, unique_name))
        image_filename = unique_name

    db.execute(
        """INSERT INTO reviews (product_id, user_id, rating, comment, image_filename)
           VALUES (?, ?, ?, ?, ?)""",
        (product_id, session["user_id"], rating_val, comment, image_filename)
    )
    db.commit()

    log_activity("review", f"Reviewed {product['name']}", product_id)
    flash("Review submitted.", "success")
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/account", methods=["GET"])
@login_required
def account():
    """show current user's profile and order history"""
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    orders = db.execute("""
        SELECT orders.*, products.name AS product_name, products.price
        FROM orders JOIN products ON orders.product_id = products.id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (session["user_id"],)).fetchall()

    return render_template("account.html", user=user, orders=orders)


@app.route("/become-seller", methods=["POST"])
@login_required
def become_seller():
    """upgrade a regular user to seller role"""
    db = get_db()
    db.execute(
        "UPDATE users SET role = 'seller' WHERE id = ? AND role = 'user'",
        (session["user_id"],)
    )
    db.commit()
    session["role"] = "seller"

    log_activity("role_upgrade", "Upgraded to seller")
    flash("You are now a seller!", "success")
    return redirect(url_for("seller_dashboard"))


# =========================================================
# Seller routes
# =========================================================

@app.route("/seller", methods=["GET"])
@role_required("seller", "admin")
def seller_dashboard():
    """seller home page - their products and sales"""
    db = get_db()
    products = db.execute(
        "SELECT * FROM products WHERE seller_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    # transaction history for products this seller owns
    transactions = db.execute("""
        SELECT orders.*, products.name AS product_name,
               users.username AS buyer, products.price
        FROM orders
        JOIN products ON orders.product_id = products.id
        JOIN users ON orders.user_id = users.id
        WHERE products.seller_id = ?
        ORDER BY orders.id DESC
    """, (session["user_id"],)).fetchall()

    return render_template(
        "seller_dashboard.html", products=products, transactions=transactions
    )


@app.route("/seller/add-product", methods=["GET", "POST"])
@role_required("seller", "admin")
def add_product():
    if request.method == "POST":
        product_form = validate_product_form(request.form)

        if product_form["errors"]:
            for e in product_form["errors"]:
                flash(e, "danger")
            return redirect(url_for("add_product"))

        db = get_db()
        db.execute(
            "INSERT INTO products (name, description, price, category, seller_id) VALUES (?, ?, ?, ?, ?)",
            (
                product_form["name"],
                product_form["description"],
                product_form["price"],
                product_form["category"],
                session["user_id"]
            )
        )
        db.commit()

        log_activity("product_add", f"Added: {product_form['name']}")
        flash("Product added.", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller_product_form.html", product=None)


@app.route("/seller/edit-product/<int:product_id>", methods=["GET", "POST"])
@role_required("seller", "admin")
def edit_product(product_id):
    db = get_db()
    product = get_product_or_404(product_id)

    # sellers can only edit their own products, admins can edit any
    if session["role"] != "admin" and product["seller_id"] != session["user_id"]:
        flash("You can only edit your own products.", "danger")
        return redirect(url_for("seller_dashboard"))

    if request.method == "POST":
        product_form = validate_product_form(request.form)

        if product_form["errors"]:
            for e in product_form["errors"]:
                flash(e, "danger")
            return redirect(url_for("edit_product", product_id=product_id))

        db.execute(
            "UPDATE products SET name = ?, description = ?, price = ?, category = ? WHERE id = ?",
            (
                product_form["name"],
                product_form["description"],
                product_form["price"],
                product_form["category"],
                product_id
            )
        )
        db.commit()

        log_activity("product_edit", f"Edited: {product_form['name']}", product_id)
        flash("Product updated.", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller_product_form.html", product=product)


# =========================================================
# Admin routes
# =========================================================

@app.route("/admin", methods=["GET"])
@role_required("admin")
def admin_dashboard():
    """admin panel - users, products, activity logs"""
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    products = db.execute("""
        SELECT products.*, users.username AS seller_name
        FROM products LEFT JOIN users ON products.seller_id = users.id
        ORDER BY products.id DESC
    """).fetchall()
    logs = db.execute("""
        SELECT activity_logs.*, users.username
        FROM activity_logs LEFT JOIN users ON activity_logs.user_id = users.id
        ORDER BY activity_logs.id DESC LIMIT 200
    """).fetchall()

    log_activity("admin_view", "Viewed admin dashboard")
    return render_template("admin.html", users=users, products=products, logs=logs)


@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def admin_change_role(user_id):
    """change another user's role"""
    new_role = request.form.get("role", "").strip()
    if new_role not in ("user", "seller", "admin"):
        flash("Invalid role.", "danger")
        return redirect(url_for("admin_dashboard"))

    # don't let admin change their own role by accident
    if user_id == session["user_id"]:
        flash("You can't change your own role.", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    db.commit()

    log_activity("admin_role_change", f"User {user_id} role -> {new_role}")
    flash("Role updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You can't delete your own account.", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    has_orders = db.execute(
        "SELECT id FROM orders WHERE user_id = ? LIMIT 1", (user_id,)
    ).fetchone()
    has_reviews = db.execute(
        "SELECT id FROM reviews WHERE user_id = ? LIMIT 1", (user_id,)
    ).fetchone()
    has_products = db.execute(
        "SELECT id FROM products WHERE seller_id = ? LIMIT 1", (user_id,)
    ).fetchone()

    if has_orders or has_reviews or has_products:
        flash("Can't delete this user because related orders, reviews, or products exist.", "danger")
        return redirect(url_for("admin_dashboard"))

    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    log_activity("admin_delete_user", f"Deleted user {user_id}")
    flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<int:product_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_product(product_id):
    db = get_db()
    has_orders = db.execute(
        "SELECT id FROM orders WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    has_reviews = db.execute(
        "SELECT id FROM reviews WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()

    if has_orders or has_reviews:
        flash("Can't delete this product because orders or reviews already exist.", "danger")
        return redirect(url_for("admin_dashboard"))

    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()

    log_activity("admin_delete_product", f"Deleted product {product_id}")
    flash("Product removed.", "success")
    return redirect(url_for("admin_dashboard"))


# create tables when the app starts so the database exists in any launch mode
with app.app_context():
    init_db()


# =========================================================
# Start the app
# =========================================================

if __name__ == "__main__":
    # debug=False for submission — never leave debug on in production
    app.run(debug=False)
