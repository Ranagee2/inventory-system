import importlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

import pandas as pd
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, or_
from werkzeug.utils import secure_filename

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret-key-change-this")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "instance", "receipts.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
LOW_STOCK_THRESHOLD = 5

# Prefer static-relative paths. These can still be overridden by env vars.
RECEIPT_BANNER_SOURCE = os.environ.get("RECEIPT_BANNER_URL", "")
PAYMENT_BARCODE_SOURCE = os.environ.get("PAYMENT_BARCODE_URL", "")

BANNER_CANDIDATES = [
    "uploads/banner.jpg",
    "uploads/banner.png",
    "banner.jpg",
    "banner.png",
    "images/banner.jpg",
    "images/banner.png",
    "assets/banner.jpg",
    "assets/banner.png",
]

BARCODE_CANDIDATES = [
    "uploads/barcode.png",
    "uploads/barcode.jpg",
    "barcode.png",
    "barcode.jpg",
    "images/barcode.png",
    "images/barcode.jpg",
    "assets/barcode.png",
    "assets/barcode.jpg",
]

TEXT = {
    "en": {
        "title": "Product Receipt System",
        "home": "Home",
        "products": "Products",
        "add_product": "Add Product",
        "edit_product": "Edit Product",
        "create_receipt": "Create Receipt",
        "receipt_details": "Receipt Details",
        "warehouse_stock": "Warehouse Stock",
        "search": "Search",
        "search_placeholder": "Search by name, size or description",
        "product_name": "Product Name",
        "price": "Price",
        "stock": "Stock",
        "size": "Size",
        "description": "Description",
        "image": "Image",
        "current_image": "Current Image",
        "optional_new_image": "Optional new image",
        "save_product": "Save Product",
        "update_product": "Update Product",
        "delete": "Delete",
        "edit": "Edit",
        "view": "View",
        "no_products": "No products found.",
        "language": "Language",
        "english": "English",
        "urdu": "Urdu",
        "customer_name": "Customer Name",
        "customer_whatsapp": "Customer WhatsApp",
        "customer_facebook": "Customer Facebook / Page URL",
        "select_product": "Select Product",
        "quantity": "Quantity",
        "submit_receipt": "Create Receipt",
        "receipt_number": "Receipt Number",
        "total_amount": "Total Amount",
        "total_items": "Total Items Purchased",
        "item_name": "Item Name",
        "item_size": "Item Size",
        "item_price": "Item Price",
        "item_quantity": "Quantity",
        "receipt_created": "Receipt created successfully.",
        "recent_receipts": "Recent Receipts",
        "view_receipt": "View Receipt",
        "no_receipts": "No receipts created yet.",
        "back": "Back",
        "manage_products": "Manage Products",
        "sale_section": "Sale / Receipt Section",
        "product_saved": "Product saved successfully.",
        "product_updated": "Product updated successfully.",
        "product_deleted": "Product deleted successfully.",
        "not_enough_stock": "Not enough stock for",
        "select_at_least_one": "Please select at least one valid product row.",
        "invalid_quantity": "Quantity must be a positive integer.",
        "invalid_price": "Price must be a valid number.",
        "invalid_stock": "Stock must be a valid integer.",
        "image_required": "Product image is required.",
        "invalid_image": "Only png, jpg, jpeg, gif, and webp files are allowed.",
        "dashboard": "Dashboard",
        "total_sales": "Total Sales",
        "today_sales": "Today Sales",
        "weekly_sales": "Weekly Sales",
        "monthly_sales": "Monthly Sales",
        "top_10_products": "Top 10 Selling Products",
        "low_stock_products": "Low Stock Products",
        "low_stock": "Low Stock",
        "out_of_stock": "Out of Stock",
        "share_product": "Share Product",
        "share_receipt": "Share Receipt",
        "share_on_whatsapp": "Share on WhatsApp",
        "share_on_facebook": "Copy for Facebook",
        "product_details": "Product Details",
        "open_product": "Open Product",
        "print_receipt": "Print Receipt",
        "copy_text": "Copy Text",
        "receipt_share_note": "This share text contains only receipt information.",
        "analytics": "Analytics",
        "sales_trend": "Sales Trend",
        "top_products_by_revenue": "Top Products by Revenue",
        "stock_status": "Stock Status",
        "quick_actions": "Quick Actions",
        "receipts": "Receipts",
        "products_count": "Products Count",
        "low_stock_count": "Low Stock",
        "out_of_stock_count": "Out of Stock",
        "customers": "Customers",
        "add_customer": "Add Customer",
        "edit_customer": "Edit Customer",
        "manage_customers": "Manage Customers",
        "select_customer": "Select Customer",
        "anonymous_customer": "Anonymous / Walk-in Customer",
        "discount_percent": "Discount %",
        "subtotal_amount": "Subtotal",
        "discount_amount": "Discount Amount",
        "customer_saved": "Customer saved successfully.",
        "customer_updated": "Customer updated successfully.",
        "customer_deleted": "Customer deleted successfully.",
        "no_customers": "No customers found.",
        "customer_profile": "Customer Profile",
        "customer_discount_applied": "Customer discount applied",
        "sync_now": "Sync Now",
        "sync_success": "Synced to cloud successfully.",
        "sync_error": "Sync failed. Will retry when online.",
        "keyboard_shortcuts": "Keyboard Shortcuts",
        "print_with_barcode": "Print with Barcode",
        "print_without_barcode": "Print without Barcode",
        "receipt_banner": "Receipt Banner",
        "payment_barcode": "Payment Barcode",
    },
    "ur": {
        "title": "پروڈکٹ رسید سسٹم",
        "home": "ہوم",
        "products": "پروڈکٹس",
        "add_product": "پروڈکٹ شامل کریں",
        "edit_product": "پروڈکٹ میں ترمیم",
        "create_receipt": "رسید بنائیں",
        "receipt_details": "رسید کی تفصیل",
        "warehouse_stock": "ویئر ہاؤس اسٹاک",
        "search": "تلاش",
        "search_placeholder": "نام، سائز یا تفصیل سے تلاش کریں",
        "product_name": "پروڈکٹ کا نام",
        "price": "قیمت",
        "stock": "اسٹاک",
        "size": "سائز",
        "description": "تفصیل",
        "image": "تصویر",
        "current_image": "موجودہ تصویر",
        "optional_new_image": "نئی تصویر اختیاری ہے",
        "save_product": "محفوظ کریں",
        "update_product": "اپڈیٹ کریں",
        "delete": "حذف کریں",
        "edit": "ترمیم",
        "view": "دیکھیں",
        "no_products": "کوئی پروڈکٹ موجود نہیں۔",
        "language": "زبان",
        "english": "انگریزی",
        "urdu": "اردو",
        "customer_name": "کسٹمر کا نام",
        "customer_whatsapp": "کسٹمر واٹس ایپ",
        "customer_facebook": "کسٹمر فیس بک / پیج URL",
        "select_product": "پروڈکٹ منتخب کریں",
        "quantity": "مقدار",
        "submit_receipt": "رسید بنائیں",
        "receipt_number": "رسید نمبر",
        "total_amount": "کل رقم",
        "total_items": "کل خریدی گئی اشیاء",
        "item_name": "آئٹم کا نام",
        "item_size": "آئٹم کا سائز",
        "item_price": "آئٹم کی قیمت",
        "item_quantity": "تعداد",
        "receipt_created": "رسید کامیابی سے بن گئی۔",
        "recent_receipts": "حالیہ رسیدیں",
        "view_receipt": "رسید دیکھیں",
        "no_receipts": "ابھی کوئی رسید نہیں بنی۔",
        "back": "واپس",
        "manage_products": "پروڈکٹس مینج کریں",
        "sale_section": "سیل / رسید سیکشن",
        "product_saved": "پروڈکٹ کامیابی سے محفوظ ہوگئی۔",
        "product_updated": "پروڈکٹ کامیابی سے اپڈیٹ ہوگئی۔",
        "product_deleted": "پروڈکٹ کامیابی سے حذف ہوگئی۔",
        "not_enough_stock": "اس پروڈکٹ کا اسٹاک کم ہے:",
        "select_at_least_one": "براہِ کرم کم از کم ایک درست پروڈکٹ منتخب کریں۔",
        "invalid_quantity": "مقدار درست positive integer ہونی چاہیے۔",
        "invalid_price": "قیمت درست نمبر ہونی چاہیے۔",
        "invalid_stock": "اسٹاک درست integer ہونا چاہیے۔",
        "image_required": "پروڈکٹ کی تصویر ضروری ہے۔",
        "invalid_image": "صرف png, jpg, jpeg, gif، اور webp فائلیں قبول ہیں۔",
        "dashboard": "ڈیش بورڈ",
        "total_sales": "کل سیلز",
        "today_sales": "آج کی سیلز",
        "weekly_sales": "ہفتہ وار سیلز",
        "monthly_sales": "ماہانہ سیلز",
        "top_10_products": "ٹاپ 10 فروخت شدہ پروڈکٹس",
        "low_stock_products": "کم اسٹاک پروڈکٹس",
        "low_stock": "کم اسٹاک",
        "out_of_stock": "اسٹاک ختم",
        "share_product": "پروڈکٹ شیئر کریں",
        "share_receipt": "رسید شیئر کریں",
        "share_on_whatsapp": "واٹس ایپ پر شیئر کریں",
        "share_on_facebook": "فیس بک کے لیے کاپی کریں",
        "product_details": "پروڈکٹ کی تفصیل",
        "open_product": "پروڈکٹ کھولیں",
        "print_receipt": "رسید پرنٹ کریں",
        "copy_text": "ٹیکسٹ کاپی کریں",
        "receipt_share_note": "اس شیئر ٹیکسٹ میں صرف رسید کی معلومات ہیں۔",
        "analytics": "اینالیٹکس",
        "sales_trend": "سیلز ٹرینڈ",
        "top_products_by_revenue": "زیادہ سیلز والی پروڈکٹس",
        "stock_status": "اسٹاک اسٹیٹس",
        "quick_actions": "فوری ایکشنز",
        "receipts": "رسیدیں",
        "products_count": "پروڈکٹس کی تعداد",
        "low_stock_count": "کم اسٹاک",
        "out_of_stock_count": "اسٹاک ختم",
        "customers": "کسٹمرز",
        "add_customer": "کسٹمر شامل کریں",
        "edit_customer": "کسٹمر میں ترمیم",
        "manage_customers": "کسٹمرز مینج کریں",
        "select_customer": "کسٹمر منتخب کریں",
        "anonymous_customer": "بغیر نام / واک اِن کسٹمر",
        "discount_percent": "ڈسکاؤنٹ %",
        "subtotal_amount": "سب ٹوٹل",
        "discount_amount": "ڈسکاؤنٹ رقم",
        "customer_saved": "کسٹمر کامیابی سے محفوظ ہوگیا۔",
        "customer_updated": "کسٹمر کامیابی سے اپڈیٹ ہوگیا۔",
        "customer_deleted": "کسٹمر کامیابی سے حذف ہوگیا۔",
        "no_customers": "کوئی کسٹمر موجود نہیں۔",
        "customer_profile": "کسٹمر پروفائل",
        "customer_discount_applied": "کسٹمر ڈسکاؤنٹ لاگو ہوگیا",
        "sync_now": "ابھی سنک کریں",
        "sync_success": "کلاؤڈ پر کامیابی سے سنک ہوگیا۔",
        "sync_error": "سنک ناکام۔ آن لائن ہونے پر دوبارہ کوشش ہوگی۔",
        "keyboard_shortcuts": "کی بورڈ شارٹس",
        "print_with_barcode": "بارکوڈ کے ساتھ پرنٹ کریں",
        "print_without_barcode": "بارکوڈ کے بغیر پرنٹ کریں",
        "receipt_banner": "رسید بینر",
        "payment_barcode": "ادائیگی بارکوڈ",
    },
}


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def t():
    lang = session.get("lang", "en")
    return TEXT.get(lang, TEXT["en"])


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_folders():
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def save_image(file_storage):
    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file_storage.save(save_path)
    return f"uploads/{unique_name}"


def remove_static_file(relative_path):
    if not relative_path:
        return
    full_path = os.path.join(app.static_folder, relative_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass


def normalize_discount(value) -> float:
    try:
        percent = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if percent < 0:
        return 0.0
    if percent > 100:
        return 100.0
    return round(percent, 2)


def money(value) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def get_supabase_sync_module():
    try:
        return importlib.import_module("supabase_sync")
    except Exception:
        return None


def is_http_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://", "//"))


def find_static_relative_by_basename(basename: str):
    static_root = app.static_folder
    if not static_root or not os.path.isdir(static_root):
        return None

    for root, _, files in os.walk(static_root):
        for file_name in files:
            if file_name.lower() == basename.lower():
                abs_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(abs_path, static_root)
                return rel_path.replace("\\", "/")
    return None


def resolve_static_asset_url(source: str, candidates: list[str]):
    """
    Returns a browser-safe URL for assets stored in /static.
    Supports:
      - full http(s) URLs
      - absolute filesystem paths
      - relative static paths like uploads/banner.jpg
      - filename search fallback inside static/
    """
    if source and is_http_url(source):
        return source

    if source:
        normalized_source = source.replace("\\", "/").lstrip("/")

        if os.path.isabs(source) and os.path.exists(source):
            try:
                rel = os.path.relpath(source, app.static_folder).replace("\\", "/")
                if not rel.startswith(".."):
                    return url_for("static", filename=rel)
            except Exception:
                pass

            basename = os.path.basename(source)
            rel_found = find_static_relative_by_basename(basename)
            if rel_found:
                return url_for("static", filename=rel_found)

        static_candidate = os.path.join(app.static_folder, normalized_source)
        if os.path.exists(static_candidate):
            return url_for("static", filename=normalized_source)

        basename = os.path.basename(normalized_source)
        rel_found = find_static_relative_by_basename(basename)
        if rel_found:
            return url_for("static", filename=rel_found)

    for candidate in candidates:
        candidate_path = os.path.join(app.static_folder, candidate)
        if os.path.exists(candidate_path):
            return url_for("static", filename=candidate)

    for candidate in candidates:
        rel_found = find_static_relative_by_basename(os.path.basename(candidate))
        if rel_found:
            return url_for("static", filename=rel_found)

    return None


def ensure_schema():
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    if "receipts" in table_names:
        existing_columns = {col["name"] for col in inspector.get_columns("receipts")}
        with db.engine.begin() as conn:
            if "customer_id" not in existing_columns:
                conn.exec_driver_sql("ALTER TABLE receipts ADD COLUMN customer_id INTEGER")
            if "subtotal_amount" not in existing_columns:
                conn.exec_driver_sql("ALTER TABLE receipts ADD COLUMN subtotal_amount FLOAT DEFAULT 0")
            if "discount_percent" not in existing_columns:
                conn.exec_driver_sql("ALTER TABLE receipts ADD COLUMN discount_percent FLOAT DEFAULT 0")
            if "discount_amount" not in existing_columns:
                conn.exec_driver_sql("ALTER TABLE receipts ADD COLUMN discount_amount FLOAT DEFAULT 0")


def build_receipt_share_text(receipt, items, labels=None):
    labels = labels or t()
    lines = [
        f"{labels['receipt_number']}: {receipt.receipt_number}",
        f"{labels['customer_name']}: {receipt.customer_name or '-'}",
        f"{labels['total_amount']}: {receipt.total_amount:.2f}",
        "",
    ]
    for item in items:
        lines.append(f"{item.product_name} x{item.quantity} = {item.line_total:.2f}")
    return "\n".join(lines)


def build_product_share_text(product):
    lines = [
        f"{product.name}",
        f"{t()['size']}: {product.size or '-'}",
        f"{t()['price']}: {product.price:.2f}",
    ]
    if product.description:
        lines.append(product.description)
    return "\n".join(lines)


def build_receipt_print_config():
    return {
        "paper": "A4",
        "font_family": "Arial, sans-serif",
        "font_size_px": 11,
        "line_height": 1.35,
        "item_image_size_px": 34,
        "table_image_size_px": 32,
        "repeat_header_on_page_break": True,
        "keep_items_together": True,
        "center_content": True,
    }


def attach_receipt_item_assets(items):
    for item in items:
        image_source = None

        if getattr(item, "product", None) and getattr(item.product, "image_path", None):
            image_source = item.product.image_path

        if not image_source and getattr(item, "product_id", None):
            product = db.session.get(Product, item.product_id)
            if product and product.image_path:
                image_source = product.image_path

        item.product_image_url = resolve_static_asset_url(
            image_source,
            ["uploads/no-image.png", "no-image.png", "placeholder.png"],
        ) if image_source else None

        item.product_image_alt = item.product_name or "Product"
        item.row_style = "page-break-inside: avoid;"

    return items


def get_receipts_df():
    receipts = Receipt.query.all()
    if not receipts:
        return pd.DataFrame(columns=["id", "total_amount", "created_at"])
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "total_amount": float(r.total_amount or 0.0),
                "created_at": r.created_at,
            }
            for r in receipts
        ]
    )


def get_receipt_items_df():
    items = ReceiptItem.query.all()
    if not items:
        return pd.DataFrame(
            columns=["id", "receipt_id", "product_id", "product_name", "product_size", "quantity", "line_total"]
        )
    return pd.DataFrame(
        [
            {
                "id": i.id,
                "receipt_id": i.receipt_id,
                "product_id": i.product_id,
                "product_name": i.product_name,
                "product_size": i.product_size,
                "quantity": int(i.quantity or 0),
                "line_total": float(i.line_total or 0.0),
            }
            for i in items
        ]
    )


def calculate_sales_stats():
    df = get_receipts_df()
    if df.empty:
        return 0.0, 0.0, 0.0, 0.0

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    now = utc_now_naive()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_sales = df["total_amount"].sum()
    today_sales = df[df["created_at"] >= today_start]["total_amount"].sum()
    weekly_sales = df[df["created_at"] >= week_start]["total_amount"].sum()
    monthly_sales = df[df["created_at"] >= month_start]["total_amount"].sum()

    return (
        round(float(total_sales), 2),
        round(float(today_sales), 2),
        round(float(weekly_sales), 2),
        round(float(monthly_sales), 2),
    )


def calculate_top_selling_products(limit=10):
    df = get_receipt_items_df()
    if df.empty:
        return []

    grouped = (
        df.groupby(["product_id", "product_name", "product_size"], dropna=False)
        .agg(sold_qty=("quantity", "sum"), revenue=("line_total", "sum"))
        .reset_index()
        .sort_values(["sold_qty", "revenue"], ascending=False)
        .head(limit)
    )

    result = []
    for _, row in grouped.iterrows():
        image_path = None
        pid = row["product_id"]
        if pd.notna(pid):
            product = db.session.get(Product, int(pid))
            if product:
                image_path = product.image_path

        result.append(
            {
                "product_id": int(pid) if pd.notna(pid) else None,
                "product_name": row["product_name"],
                "product_size": row["product_size"],
                "sold_qty": int(row["sold_qty"]),
                "revenue": round(float(row["revenue"]), 2),
                "image_path": image_path,
            }
        )
    return result


def calculate_sales_trend(days=30):
    df = get_receipts_df()
    end_date = utc_now_naive().date()
    start_date = end_date - timedelta(days=days - 1)
    dates = [start_date + timedelta(days=i) for i in range(days)]

    if df.empty:
        return [d.strftime("%d %b") for d in dates], [0.0 for _ in dates]

    df["created_date"] = pd.to_datetime(df["created_at"], errors="coerce").dt.date
    grouped = df.groupby("created_date")["total_amount"].sum()
    labels = [d.strftime("%d %b") for d in dates]
    values = [round(float(grouped.get(d, 0.0)), 2) for d in dates]
    return labels, values


def calculate_monthly_sales(months=6):
    df = get_receipts_df()
    current_period = pd.Timestamp.now(tz="UTC").tz_localize(None).to_period("M")
    periods = [current_period - i for i in reversed(range(months))]

    if df.empty:
        return [p.strftime("%b %Y") for p in periods], [0.0 for _ in periods]

    df["month_period"] = pd.to_datetime(df["created_at"], errors="coerce").dt.to_period("M")
    grouped = df.groupby("month_period")["total_amount"].sum()
    labels = [p.strftime("%b %Y") for p in periods]
    values = [round(float(grouped.get(p, 0.0)), 2) for p in periods]
    return labels, values


def calculate_stock_distribution():
    products = Product.query.all()
    total = len(products)
    low = sum(1 for p in products if 0 < p.quantity <= LOW_STOCK_THRESHOLD)
    out = sum(1 for p in products if p.quantity == 0)
    healthy = max(total - low - out, 0)
    return {
        "labels": [t()["products"], t()["low_stock"], t()["out_of_stock"]],
        "values": [healthy, low, out],
    }


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    image_path = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    size = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now_naive)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    whatsapp = db.Column(db.String(50), nullable=True)
    facebook = db.Column(db.String(255), nullable=True)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=utc_now_naive)


class Receipt(db.Model):
    __tablename__ = "receipts"
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(60), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    customer = db.relationship("Customer", lazy="joined")
    customer_name = db.Column(db.String(150), nullable=True)
    customer_whatsapp = db.Column(db.String(50), nullable=True)
    customer_facebook = db.Column(db.String(255), nullable=True)
    subtotal_amount = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=utc_now_naive)
    items = db.relationship(
        "ReceiptItem",
        backref="receipt",
        cascade="all, delete-orphan",
        lazy=True,
    )


class ReceiptItem(db.Model):
    __tablename__ = "receipt_items"
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product = db.relationship("Product", lazy="joined")
    product_name = db.Column(db.String(150), nullable=False)
    product_size = db.Column(db.String(50), nullable=True)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    line_total = db.Column(db.Float, nullable=False, default=0.0)


@app.route("/lang/<code>")
def set_lang(code):
    if code in TEXT:
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


@app.route("/")
def index():
    ensure_folders()
    query = request.args.get("q", "").strip()

    product_query = Product.query
    if query:
        like = f"%{query}%"
        product_query = product_query.filter(
            or_(
                Product.name.ilike(like),
                Product.size.ilike(like),
                Product.description.ilike(like),
            )
        )

    products = product_query.order_by(Product.id.desc()).all()
    recent_receipts = Receipt.query.order_by(Receipt.id.desc()).limit(5).all()
    low_stock_products = (
        Product.query.filter(Product.quantity <= LOW_STOCK_THRESHOLD)
        .order_by(Product.quantity.asc(), Product.name.asc())
        .limit(8)
        .all()
    )
    total_sales, today_sales, weekly_sales, monthly_sales = calculate_sales_stats()
    top_selling_products = calculate_top_selling_products()
    sales_labels, sales_values = calculate_sales_trend()
    month_labels, month_values = calculate_monthly_sales()
    stock_distribution = calculate_stock_distribution()

    supabase_module = get_supabase_sync_module()
    supabase_enabled = bool(supabase_module and hasattr(supabase_module, "is_enabled") and supabase_module.is_enabled())

    return render_template(
        "index.html",
        page="home",
        t=t(),
        lang=session.get("lang", "en"),
        products=products,
        recent_receipts=recent_receipts,
        low_stock_products=low_stock_products,
        query=query,
        total_sales=total_sales,
        today_sales=today_sales,
        weekly_sales=weekly_sales,
        monthly_sales=monthly_sales,
        top_selling_products=top_selling_products,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
        sales_labels=sales_labels,
        sales_values=sales_values,
        month_labels=month_labels,
        month_values=month_values,
        stock_distribution=stock_distribution,
        products_count=Product.query.count(),
        receipts_count=Receipt.query.count(),
        customers_count=Customer.query.count(),
        low_stock_count=Product.query.filter(Product.quantity <= LOW_STOCK_THRESHOLD).count(),
        out_of_stock_count=Product.query.filter(Product.quantity == 0).count(),
        supabase_enabled=supabase_enabled,
    )


@app.route("/api/sync/push", methods=["POST"])
def api_sync_push():
    supabase_module = get_supabase_sync_module()
    if not supabase_module or not hasattr(supabase_module, "is_enabled"):
        return jsonify({"ok": False, "error": "supabase_sync module not found or not enabled."})
    try:
        if not supabase_module.is_enabled():
            return jsonify({"ok": False, "error": "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY env vars."})
        result = supabase_module.push_all(app.app_context())
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@app.route("/api/sync/status", methods=["GET"])
def api_sync_status():
    supabase_module = get_supabase_sync_module()
    if not supabase_module or not hasattr(supabase_module, "is_enabled"):
        return jsonify({"enabled": False})
    return jsonify({"enabled": bool(supabase_module.is_enabled())})


@app.route("/customers", methods=["GET", "POST"])
def customers():
    ensure_folders()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        facebook = request.form.get("facebook", "").strip()
        discount_percent = normalize_discount(request.form.get("discount_percent"))

        errors = []
        if not name:
            errors.append("Customer name is required.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                customer = Customer(
                    name=name,
                    whatsapp=whatsapp,
                    facebook=facebook,
                    discount_percent=discount_percent,
                )
                db.session.add(customer)
                db.session.commit()
                flash(t()["customer_saved"], "success")
                return redirect(url_for("customers"))
            except Exception as exc:
                db.session.rollback()
                flash(f"Error: {exc}", "danger")

    customer_list = Customer.query.order_by(Customer.id.desc()).all()
    return render_template(
        "index.html",
        page="customers",
        t=t(),
        lang=session.get("lang", "en"),
        customers_list=customer_list,
        form_mode="add",
        form_action=url_for("customers"),
    )


@app.route("/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    ensure_folders()
    customer = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        facebook = request.form.get("facebook", "").strip()
        discount_percent = normalize_discount(request.form.get("discount_percent"))

        errors = []
        if not name:
            errors.append("Customer name is required.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                customer.name = name
                customer.whatsapp = whatsapp
                customer.facebook = facebook
                customer.discount_percent = discount_percent
                db.session.commit()
                flash(t()["customer_updated"], "success")
                return redirect(url_for("customers"))
            except Exception as exc:
                db.session.rollback()
                flash(f"Error: {exc}", "danger")

    return render_template(
        "index.html",
        page="customer_form",
        t=t(),
        lang=session.get("lang", "en"),
        customer=customer,
        form_mode="edit",
        form_action=url_for("edit_customer", customer_id=customer.id),
    )


@app.route("/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        Receipt.query.filter_by(customer_id=customer.id).update(
            {"customer_id": None},
            synchronize_session=False,
        )
        db.session.delete(customer)
        db.session.commit()
        flash(t()["customer_deleted"], "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error: {exc}", "danger")
    return redirect(url_for("customers"))


@app.route("/products/<int:product_id>")
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    product_share_text = build_product_share_text(product)
    return render_template(
        "index.html",
        page="product_detail",
        t=t(),
        lang=session.get("lang", "en"),
        product=product,
        product_share_text=product_share_text,
        product_whatsapp_share_url=f"https://wa.me/?text={quote_plus(product_share_text)}",
    )


@app.route("/products/new", methods=["GET", "POST"])
def add_product():
    ensure_folders()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price_raw = request.form.get("price", "").strip()
        quantity_raw = request.form.get("quantity", "").strip()
        size = request.form.get("size", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("image")

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not price_raw:
            errors.append(t()["invalid_price"])
        if not quantity_raw:
            errors.append(t()["invalid_stock"])
        if not image or not image.filename:
            errors.append(t()["image_required"])
        elif not allowed_file(image.filename):
            errors.append(t()["invalid_image"])

        try:
            price = float(price_raw)
            if price < 0:
                errors.append(t()["invalid_price"])
        except ValueError:
            errors.append(t()["invalid_price"])

        try:
            quantity = int(quantity_raw)
            if quantity < 0:
                errors.append(t()["invalid_stock"])
        except ValueError:
            errors.append(t()["invalid_stock"])

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                image_path = save_image(image)
                product = Product(
                    name=name,
                    price=price,
                    quantity=quantity,
                    size=size,
                    description=description,
                    image_path=image_path,
                )
                db.session.add(product)
                db.session.commit()
                flash(t()["product_saved"], "success")
                return redirect(url_for("index"))
            except Exception as exc:
                db.session.rollback()
                flash(f"Error: {exc}", "danger")

    return render_template(
        "index.html",
        page="product_form",
        form_mode="add",
        t=t(),
        lang=session.get("lang", "en"),
        product=None,
        form_action=url_for("add_product"),
    )


@app.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    ensure_folders()
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price_raw = request.form.get("price", "").strip()
        quantity_raw = request.form.get("quantity", "").strip()
        size = request.form.get("size", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("image")

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not price_raw:
            errors.append(t()["invalid_price"])
        if not quantity_raw:
            errors.append(t()["invalid_stock"])

        try:
            price = float(price_raw)
            if price < 0:
                errors.append(t()["invalid_price"])
        except ValueError:
            errors.append(t()["invalid_price"])

        try:
            quantity = int(quantity_raw)
            if quantity < 0:
                errors.append(t()["invalid_stock"])
        except ValueError:
            errors.append(t()["invalid_stock"])

        if image and image.filename and not allowed_file(image.filename):
            errors.append(t()["invalid_image"])

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                product.name = name
                product.price = price
                product.quantity = quantity
                product.size = size
                product.description = description
                if image and image.filename:
                    if product.image_path:
                        remove_static_file(product.image_path)
                    product.image_path = save_image(image)
                db.session.commit()
                flash(t()["product_updated"], "success")
                return redirect(url_for("index"))
            except Exception as exc:
                db.session.rollback()
                flash(f"Error: {exc}", "danger")

    return render_template(
        "index.html",
        page="product_form",
        form_mode="edit",
        t=t(),
        lang=session.get("lang", "en"),
        product=product,
        form_action=url_for("edit_product", product_id=product.id),
    )


@app.route("/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        ReceiptItem.query.filter_by(product_id=product.id).update(
            {"product_id": None},
            synchronize_session=False,
        )
        if product.image_path:
            remove_static_file(product.image_path)
        db.session.delete(product)
        db.session.commit()
        flash(t()["product_deleted"], "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error: {exc}", "danger")
    return redirect(url_for("index"))


@app.route("/receipt/new", methods=["GET", "POST"])
def create_receipt():
    ensure_folders()
    products = Product.query.order_by(Product.name.asc()).all()
    customer_list = Customer.query.order_by(Customer.name.asc()).all()

    if request.method == "POST":
        customer_id_raw = request.form.get("customer_id", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        customer_whatsapp = request.form.get("customer_whatsapp", "").strip()
        customer_facebook = request.form.get("customer_facebook", "").strip()
        product_ids = request.form.getlist("product_id")
        quantities = request.form.getlist("quantity")

        errors = []
        items_to_save = []
        customer = None
        customer_discount_percent = 0.0

        if customer_id_raw:
            try:
                customer = db.session.get(Customer, int(customer_id_raw))
            except ValueError:
                customer = None

        if customer:
            customer_name = customer.name
            customer_whatsapp = customer.whatsapp or ""
            customer_facebook = customer.facebook or ""
            customer_discount_percent = normalize_discount(customer.discount_percent)

        for pid_raw, qty_raw in zip(product_ids, quantities):
            pid_raw = (pid_raw or "").strip()
            qty_raw = (qty_raw or "").strip()
            if not pid_raw or not qty_raw:
                continue
            try:
                pid = int(pid_raw)
                qty = int(qty_raw)
            except ValueError:
                continue
            if qty <= 0:
                continue
            product = db.session.get(Product, pid)
            if not product:
                continue
            if product.quantity < qty:
                errors.append(f"{t()['not_enough_stock']} {product.name}")
                continue
            items_to_save.append((product, qty))

        if not items_to_save:
            errors.append(t()["select_at_least_one"])

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                receipt_number = f"RCPT-{utc_now_naive().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                receipt = Receipt(
                    receipt_number=receipt_number,
                    customer_id=customer.id if customer else None,
                    customer_name=customer_name,
                    customer_whatsapp=customer_whatsapp,
                    customer_facebook=customer_facebook,
                    subtotal_amount=0.0,
                    discount_percent=customer_discount_percent,
                    discount_amount=0.0,
                    total_amount=0.0,
                )
                db.session.add(receipt)
                db.session.flush()

                rows = []
                for product, qty in items_to_save:
                    rows.append({"product_id": product.id, "price": float(product.price), "qty": int(qty)})

                df_items = pd.DataFrame(rows)
                df_items["gross_total"] = df_items["price"] * df_items["qty"]
                subtotal = round(float(df_items["gross_total"].sum()), 2)
                discount_amount = round(subtotal * (customer_discount_percent / 100.0), 2)
                total_amount = round(subtotal - discount_amount, 2)

                for idx, (product, qty) in enumerate(items_to_save):
                    gross_line_total = float(df_items.loc[idx, "gross_total"])
                    line_discount = round(gross_line_total * (customer_discount_percent / 100.0), 2)
                    line_total = round(gross_line_total - line_discount, 2)
                    item = ReceiptItem(
                        receipt_id=receipt.id,
                        product_id=product.id,
                        product_name=product.name,
                        product_size=product.size,
                        unit_price=product.price,
                        quantity=qty,
                        line_total=line_total,
                    )
                    db.session.add(item)
                    product.quantity -= qty

                receipt.subtotal_amount = subtotal
                receipt.discount_percent = customer_discount_percent
                receipt.discount_amount = discount_amount
                receipt.total_amount = total_amount
                db.session.commit()
                flash(t()["receipt_created"], "success")
                return redirect(url_for("view_receipt", receipt_id=receipt.id))
            except Exception as exc:
                db.session.rollback()
                flash(f"Error: {exc}", "danger")

    return render_template(
        "index.html",
        page="receipt_form",
        t=t(),
        lang=session.get("lang", "en"),
        products=products,
        customers_list=customer_list,
        rows=range(1, 11),
    )


@app.route("/receipt/<int:receipt_id>")
def view_receipt(receipt_id):
    receipt = Receipt.query.get_or_404(receipt_id)
    items = ReceiptItem.query.filter_by(receipt_id=receipt.id).all()

    df = pd.DataFrame([{"quantity": i.quantity} for i in items]) if items else pd.DataFrame({"quantity": []})
    total_items = int(df["quantity"].sum()) if not df.empty else 0

    receipt_labels = TEXT["ur"]
    receipt_share_text = build_receipt_share_text(receipt, items, receipt_labels)

    show_payment_barcode = request.args.get("barcode", "1") != "0"
    autoprint = request.args.get("autoprint", "0") == "1"

    items = attach_receipt_item_assets(items)

    receipt_banner_url = resolve_static_asset_url(RECEIPT_BANNER_SOURCE, BANNER_CANDIDATES)
    payment_barcode_url = resolve_static_asset_url(PAYMENT_BARCODE_SOURCE, BARCODE_CANDIDATES)

    return render_template(
        "index.html",
        page="receipt_detail",
        t=t(),
        receipt_t=receipt_labels,
        lang=session.get("lang", "en"),
        receipt=receipt,
        items=items,
        total_items=total_items,
        receipt_share_text=receipt_share_text,
        receipt_whatsapp_share_url=f"https://wa.me/?text={quote_plus(receipt_share_text)}",
        receipt_banner_url=receipt_banner_url,
        payment_barcode_url=payment_barcode_url,
        show_payment_barcode=show_payment_barcode,
        autoprint=autoprint,
        receipt_print_config=build_receipt_print_config(),
        receipt_page_mode="A4",
    )


if __name__ == "__main__":
    ensure_folders()
    with app.app_context():
        db.create_all()
        ensure_schema()
    app.run(debug=True)