import os
import secrets

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from ..utils.db import get_db, get_product_or_404, log_activity
from ..utils.security import login_required
from ..utils.validators import MAX_COMMENT_LEN, allowed_file


products_bp = Blueprint("products", __name__)


@products_bp.route("/", methods=["GET"])
def index():
    # The homepage shows products and supports a simple search and category filter.
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

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
        "index.html",
        products=products,
        categories=categories,
        search=search,
        current_category=category,
    )


@products_bp.route("/product/<int:product_id>", methods=["GET"])
def product_detail(product_id):
    # This page shows one product and the reviews linked to it.
    db = get_db()
    product = get_product_or_404(product_id)

    reviews = db.execute(
        """
        SELECT reviews.*, users.username
        FROM reviews JOIN users ON reviews.user_id = users.id
        WHERE reviews.product_id = ?
        ORDER BY reviews.id DESC
        """,
        (product_id,),
    ).fetchall()

    has_purchased = False
    if "user_id" in session:
        order = db.execute(
            "SELECT id FROM orders WHERE user_id = ? AND product_id = ?",
            (session["user_id"], product_id),
        ).fetchone()
        has_purchased = order is not None

    log_activity("product_view", product["name"], product_id)

    return render_template(
        "product.html",
        product=product,
        reviews=reviews,
        has_purchased=has_purchased,
    )


@products_bp.route("/product/<int:product_id>/buy", methods=["POST"])
@login_required
def buy_product(product_id):
    # Buying a product just records an order row for this coursework prototype.
    db = get_db()
    product = get_product_or_404(product_id)

    quantity = request.form.get("quantity", "1").strip()
    try:
        quantity_value = int(quantity)
    except ValueError:
        flash("Invalid quantity.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    if quantity_value < 1 or quantity_value > 99:
        flash("Quantity must be between 1 and 99.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    db.execute(
        "INSERT INTO orders (user_id, product_id, quantity) VALUES (?, ?, ?)",
        (session["user_id"], product_id, quantity_value),
    )
    db.commit()

    log_activity("purchase", f"Bought {quantity_value}x {product['name']}", product_id)
    flash("Purchase complete!", "success")
    return redirect(url_for("product_detail", product_id=product_id))


@products_bp.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
def add_review(product_id):
    # Reviews are only allowed if the logged-in user has already bought the product.
    db = get_db()
    product = get_product_or_404(product_id)

    order = db.execute(
        "SELECT id FROM orders WHERE user_id = ? AND product_id = ?",
        (session["user_id"], product_id),
    ).fetchone()
    if not order:
        flash("You can only review products you have purchased.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    try:
        rating_value = int(rating)
    except (ValueError, TypeError):
        flash("Please select a rating.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    if rating_value < 1 or rating_value > 5:
        flash("Rating must be between 1 and 5.", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    if not comment or len(comment) > MAX_COMMENT_LEN:
        flash(f"Comment is required (max {MAX_COMMENT_LEN} characters).", "danger")
        return redirect(url_for("product_detail", product_id=product_id))

    image_filename = None
    uploaded_file = request.files.get("image")
    if uploaded_file and uploaded_file.filename:
        if not allowed_file(uploaded_file.filename):
            flash("Only png, jpg, jpeg, webp images are allowed.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        if not uploaded_file.mimetype or not uploaded_file.mimetype.startswith("image/"):
            flash("Uploaded file must be a real image type.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))

        safe_name = secure_filename(uploaded_file.filename)
        unique_name = f"{secrets.token_hex(8)}_{safe_name}"
        upload_folder = os.path.join(current_app.static_folder, "uploads")
        uploaded_file.save(os.path.join(upload_folder, unique_name))
        image_filename = unique_name

    db.execute(
        """
        INSERT INTO reviews (product_id, user_id, rating, comment, image_filename)
        VALUES (?, ?, ?, ?, ?)
        """,
        (product_id, session["user_id"], rating_value, comment, image_filename),
    )
    db.commit()

    log_activity("review", f"Reviewed {product['name']}", product_id)
    flash("Review submitted.", "success")
    return redirect(url_for("product_detail", product_id=product_id))


@products_bp.route("/account", methods=["GET"])
@login_required
def account():
    # The account page shows the logged-in user's details and order history.
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    orders = db.execute(
        """
        SELECT orders.*, products.name AS product_name, products.price
        FROM orders JOIN products ON orders.product_id = products.id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    return render_template("account.html", user=user, orders=orders)
