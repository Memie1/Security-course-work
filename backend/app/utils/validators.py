import re

from .security import ALLOWED_EXTENSIONS


USERNAME_RE = re.compile(r"^\w{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
MAX_COMMENT_LEN = 2000


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_product_form(form_data):
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
