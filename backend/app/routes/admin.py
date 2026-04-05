from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..utils.db import get_db, log_activity
from ..utils.security import role_required


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET"])
@role_required("admin")
def admin_dashboard():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    products = db.execute(
        """
        SELECT products.*, users.username AS seller_name
        FROM products LEFT JOIN users ON products.seller_id = users.id
        ORDER BY products.id DESC
        """
    ).fetchall()
    logs = db.execute(
        """
        SELECT activity_logs.*, users.username
        FROM activity_logs LEFT JOIN users ON activity_logs.user_id = users.id
        ORDER BY activity_logs.id DESC LIMIT 200
        """
    ).fetchall()

    log_activity("admin_view", "Viewed admin dashboard")
    return render_template("admin.html", users=users, products=products, logs=logs)


@admin_bp.route("/admin/user/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def admin_change_role(user_id):
    new_role = request.form.get("role", "").strip()
    if new_role not in ("user", "seller", "admin"):
        flash("Invalid role.", "danger")
        return redirect(url_for("admin_dashboard"))

    if user_id == session["user_id"]:
        flash("You can't change your own role.", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    db.commit()

    log_activity("admin_role_change", f"User {user_id} role -> {new_role}")
    flash("Role updated.", "success")
    return redirect(url_for("admin_dashboard"))


@admin_bp.route("/admin/user/<int:user_id>/delete", methods=["POST"])
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


@admin_bp.route("/admin/product/<int:product_id>/delete", methods=["POST"])
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
