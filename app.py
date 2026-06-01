"""Expense Tracker - Flask web application."""

from datetime import date

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

import database as db
import export_excel
import receipts

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # 6 MB request limit


@app.before_request
def ensure_db():
    if not hasattr(app, "_db_initialized"):
        db.init_db()
        receipts.ensure_upload_dir()
        app._db_initialized = True


@app.route("/")
def index():
    return render_template(
        "index.html",
        categories=db.CATEGORIES,
        current_month=date.today().strftime("%Y-%m"),
    )


@app.route("/dashboard")
def dashboard():
    current_year = date.today().strftime("%Y")
    years = db.get_available_years()
    if current_year not in years:
        years.insert(0, current_year)
    return render_template(
        "dashboard.html",
        categories=db.CATEGORIES,
        years=years,
        current_year=current_year,
        current_month=date.today().strftime("%m"),
    )


@app.route("/uploads/receipts/<path:filename>")
def serve_receipt(filename):
    return send_from_directory(receipts.UPLOAD_DIR, filename)


@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    month = request.args.get("month")
    category = request.args.get("category")
    return jsonify(db.get_expenses(month=month, category=category))


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    data = request.form
    receipt_file = request.files.get("receipt")

    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"error": "Description is required"}), 400

    category = data.get("category", "Other")
    if category not in db.CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400

    expense_date = data.get("expense_date") or date.today().isoformat()

    receipt_path = None
    if receipt_file and receipt_file.filename:
        try:
            receipt_path = receipts.save_receipt(receipt_file)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    expense_id = db.add_expense(
        amount, description, category, expense_date, receipt_path
    )
    expense = db.get_expense(expense_id)
    return jsonify(expense), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def remove_expense(expense_id):
    deleted, receipt_path = db.delete_expense(expense_id)
    if deleted:
        receipts.delete_receipt(receipt_path)
        return jsonify({"message": "Expense deleted"})
    return jsonify({"error": "Expense not found"}), 404


@app.route("/api/summary")
def summary():
    month = request.args.get("month")
    return jsonify(db.get_summary(month=month))


@app.route("/api/dashboard")
def dashboard_data():
    year = request.args.get("year") or date.today().strftime("%Y")
    month = request.args.get("month") or None
    category = request.args.get("category") or None

    if month and (not month.isdigit() or int(month) < 1 or int(month) > 12):
        return jsonify({"error": "Invalid month"}), 400

    if category and category not in db.CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400

    return jsonify(db.get_dashboard_data(year=year, month=month, category=category))


@app.route("/api/categories")
def categories():
    return jsonify(db.CATEGORIES)


@app.route("/api/expenses/export")
def export_expenses():
    buffer, filename = export_excel.export_all_expenses()
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    db.init_db()
    receipts.ensure_upload_dir()
    app.run(debug=True, port=5000)
