from flask import Blueprint, request, jsonify
from models import Expense, Category, Report
from database import db
from datetime import datetime
from routes.utils import get_user_id

expenses_bp = Blueprint("expenses", __name__)


#  Add Expense 
@expenses_bp.route("/", methods=["POST"])
def add_expense():
    uid = get_user_id()
    if not uid:
        return jsonify({"error": "No user found. Please register first."}), 400

    data = request.get_json()

    if not data.get("amount") or not data.get("date"):
        return jsonify({"error": "amount and date are required"}), 400

    try:
        amount = float(data["amount"])
        if amount <= 0:
            return jsonify({"error": "amount must be greater than 0"}), 400

        date = datetime.strptime(data["date"], "%Y-%m-%d").date()

        # Validate categoryID is a real category if provided
        category_id = data.get("categoryID")
        if category_id:
            category_id = int(category_id)
            if not Category.query.get(category_id):
                return jsonify({"error": "Invalid category"}), 400

        expense = Expense(
            amount=amount,
            date=date,
            description=data.get("description", "").strip(),
            categoryID=category_id,
            userID=uid,
        )
        db.session.add(expense)
        db.session.commit()

    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400

    return jsonify(expense.to_dict()), 201


#  Get Expenses (with optional filters) 
@expenses_bp.route("/", methods=["GET"])
def get_expenses():
    uid = get_user_id()
    if not uid:
        return jsonify([]), 200

    query = Expense.query.filter_by(userID=uid)

    category_id = request.args.get("categoryID")
    if category_id:
        try:
            query = query.filter_by(categoryID=int(category_id))
        except ValueError:
            return jsonify({"error": "Invalid categoryID"}), 400

    month = request.args.get("month")
    if month:
        try:
            year, mon = map(int, month.split("-"))
            query = query.filter(
                db.extract("year", Expense.date) == year,
                db.extract("month", Expense.date) == mon,
            )
        except ValueError:
            return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    expenses = query.order_by(Expense.date.desc()).all()
    return jsonify([e.to_dict() for e in expenses]), 200


#  Category Breakdown — spending per category 
@expenses_bp.route("/by-category", methods=["GET"])
def by_category():
    """
    Total spending grouped by category. Optional ?month=YYYY-MM filter.
    Covers: 'organize expenses into categories' and 'category-specific habits'.
    """
    uid = get_user_id()
    if not uid:
        return jsonify([]), 200

    query = Expense.query.filter_by(userID=uid)

    month = request.args.get("month")
    if month:
        try:
            year, mon = map(int, month.split("-"))
            query = query.filter(
                db.extract("year", Expense.date) == year,
                db.extract("month", Expense.date) == mon,
            )
        except ValueError:
            return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    expenses = query.all()

    totals = {}
    for e in expenses:
        name = e.category.name if e.category else "Uncategorized"
        totals[name] = round(totals.get(name, 0) + e.amount, 2)

    grand_total = sum(totals.values())
    result = [
        {
            "category":   cat,
            "total":      amount,
            "percentage": round((amount / grand_total) * 100, 1) if grand_total > 0 else 0,
        }
        for cat, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return jsonify(result), 200


#  Update Expense 
@expenses_bp.route("/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    uid = get_user_id()
    expense = Expense.query.filter_by(expenseID=expense_id, userID=uid).first()

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    data = request.get_json()

    if "date" in data:
        try:
            data["date"] = datetime.strptime(data["date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if "amount" in data:
        try:
            data["amount"] = float(data["amount"])
            if data["amount"] <= 0:
                return jsonify({"error": "amount must be greater than 0"}), 400
        except ValueError:
            return jsonify({"error": "Invalid amount"}), 400

    if "categoryID" in data and data["categoryID"]:
        try:
            data["categoryID"] = int(data["categoryID"])
            if not Category.query.get(data["categoryID"]):
                return jsonify({"error": "Invalid category"}), 400
        except ValueError:
            return jsonify({"error": "Invalid categoryID"}), 400

    expense.edit(data)
    db.session.commit()
    return jsonify(expense.to_dict()), 200


#  Delete Expense 
@expenses_bp.route("/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    uid = get_user_id()
    expense = Expense.query.filter_by(expenseID=expense_id, userID=uid).first()

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    expense.delete()
    return jsonify({"message": "Expense deleted"}), 200


#  Export CSV 
# NOTE: This route must stay BELOW the /<int:expense_id> routes so Flask
# does not try to parse "export" as an integer ID.
@expenses_bp.route("/export", methods=["GET"])
def export_csv():
    uid = get_user_id()
    if not uid:
        return jsonify({"error": "No user found"}), 400

    query = Expense.query.filter_by(userID=uid)

    month = request.args.get("month")
    if month:
        try:
            year, mon = map(int, month.split("-"))
            query = query.filter(
                db.extract("year", Expense.date) == year,
                db.extract("month", Expense.date) == mon,
            )
        except ValueError:
            return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    expenses = query.order_by(Expense.date.desc()).all()
    report = Report(expenses)
    return report.download()


#  Get All Categories 
@expenses_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories]), 200