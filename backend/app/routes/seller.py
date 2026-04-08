from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..utils.db import get_db, get_product_or_404, log_activity
from ..utils.security import login_required, role_required
from ..utils.validators import validate_product_form


seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/become-seller", methods=["POST"])
@login_required
def become_seller():
    # This upgrades a normal user account to the seller role.
    db = get_db()
    db.execute(
        "UPDATE users SET role = 'seller' WHERE id = ? AND role = 'user'",
        (session["user_id"],),
    )
    db.commit()
    session["role"] = "seller"

    log_activity("role_upgrade", "Upgraded to seller")
    flash("You are now a seller!", "success")
    return redirect(url_for("seller_dashboard"))


@seller_bp.route("/seller", methods=["GET"])
@role_required("seller", "admin")
def seller_dashboard():
    # Sellers can see their own products and the orders linked to them here.
    db = get_db()
    products = db.execute(
        "SELECT * FROM products WHERE seller_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()

    transactions = db.execute(
        """
        SELECT orders.*, products.name AS product_name,
               users.username AS buyer, products.price
        FROM orders
        JOIN products ON orders.product_id = products.id
        JOIN users ON orders.user_id = users.id
        WHERE products.seller_id = ?
        ORDER BY orders.id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    return render_template(
        "seller_dashboard.html",
        products=products,
        transactions=transactions,
    )


@seller_bp.route("/seller/add-product", methods=["GET", "POST"])
@role_required("seller", "admin")
def add_product():
    # This route lets a seller create a new product listing.
    if request.method == "POST":
        product_form = validate_product_form(request.form)

        if product_form["errors"]:
            for error in product_form["errors"]:
                flash(error, "danger")
            return redirect(url_for("add_product"))

        db = get_db()
        db.execute(
            "INSERT INTO products (name, description, price, category, seller_id) VALUES (?, ?, ?, ?, ?)",
            (
                product_form["name"],
                product_form["description"],
                product_form["price"],
                product_form["category"],
                session["user_id"],
            ),
        )
        db.commit()

        log_activity("product_add", f"Added: {product_form['name']}")
        flash("Product added.", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller_product_form.html", product=None)


@seller_bp.route("/seller/edit-product/<int:product_id>", methods=["GET", "POST"])
@role_required("seller", "admin")
def edit_product(product_id):
    # Sellers can edit their own products, and admins can edit any product.
    db = get_db()
    product = get_product_or_404(product_id)

    if session["role"] != "admin" and product["seller_id"] != session["user_id"]:
        flash("You can only edit your own products.", "danger")
        return redirect(url_for("seller_dashboard"))

    if request.method == "POST":
        product_form = validate_product_form(request.form)

        if product_form["errors"]:
            for error in product_form["errors"]:
                flash(error, "danger")
            return redirect(url_for("edit_product", product_id=product_id))

        db.execute(
            "UPDATE products SET name = ?, description = ?, price = ?, category = ? WHERE id = ?",
            (
                product_form["name"],
                product_form["description"],
                product_form["price"],
                product_form["category"],
                product_id,
            ),
        )
        db.commit()

        log_activity("product_edit", f"Edited: {product_form['name']}", product_id)
        flash("Product updated.", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller_product_form.html", product=product)
