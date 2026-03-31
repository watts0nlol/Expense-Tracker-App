from flask import Blueprint, request, jsonify
from models import Expense, Analytics, SpendingGoal, Reflection, Notification
from database import db
from datetime import datetime
from routes.utils import get_user_id

analytics_bp = Blueprint("analytics", __name__)


def _get_prev_month(month: str) -> str:
    """Returns the previous month string given a YYYY-MM string."""
    year, mon = map(int, month.split("-"))
    if mon == 1:
        return f"{year - 1}-12"
    return f"{year}-{str(mon - 1).padStart(2, '0')}"


def _expenses_for_month(uid: int, month: str) -> list:
    """Helper: fetch all expenses for a user in a given YYYY-MM month."""
    year, mon = map(int, month.split("-"))
    return Expense.query.filter(
        Expense.userID == uid,
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == mon,
    ).all()


# ── Monthly Summary — spending totals + category breakdown ───────────────────
@analytics_bp.route("/summary", methods=["GET"])
def monthly_summary():
    """
    Covers: 'display simple summaries' and 'category-specific spending habits'.
    Returns total spent + per-category breakdown for a given month.
    """
    uid = get_user_id()
    if not uid:
        return jsonify({"month": "", "total": 0, "breakdown": []}), 200

    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))
    try:
        year, mon = map(int, month.split("-"))
    except ValueError:
        return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    expenses = Expense.query.filter(
        Expense.userID == uid,
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == mon,
    ).all()

    analytics = Analytics(expenses)
    total = analytics.totalSpent
    breakdown = [
        {
            "category":   cat,
            "total":      round(amount, 2),
            "percentage": round((amount / total) * 100, 1) if total > 0 else 0,
        }
        for cat, amount in analytics.categoryBreakdown.items()
    ]

    return jsonify({
        "month":     month,
        "total":     total,
        "breakdown": sorted(breakdown, key=lambda x: x["total"], reverse=True),
    }), 200


# ── Insights — highlights + month-over-month change ──────────────────────────
@analytics_bp.route("/insights", methods=["GET"])
def insights():
    """
    Covers: 'highlighting the month's highest-spending category' and
    'showing how spending has changed from the previous month'.
    Returns both in a single response so the dashboard only needs one call.
    """
    uid = get_user_id()
    if not uid:
        return jsonify({}), 200

    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))
    try:
        year, mon = map(int, month.split("-"))
    except ValueError:
        return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    # Previous month
    prev_year, prev_mon = (year - 1, 12) if mon == 1 else (year, mon - 1)
    prev_month = f"{prev_year}-{str(prev_mon).zfill(2)}"

    curr_expenses = Expense.query.filter(
        Expense.userID == uid,
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == mon,
    ).all()

    prev_expenses = Expense.query.filter(
        Expense.userID == uid,
        db.extract("year", Expense.date) == prev_year,
        db.extract("month", Expense.date) == prev_mon,
    ).all()

    curr_analytics = Analytics(curr_expenses)
    prev_analytics = Analytics(prev_expenses)

    curr_total = curr_analytics.totalSpent
    prev_total = prev_analytics.totalSpent

    # Highest spending category this month
    top_category = None
    if curr_analytics.categoryBreakdown:
        top_cat_name = max(curr_analytics.categoryBreakdown, key=curr_analytics.categoryBreakdown.get)
        top_category = {
            "category": top_cat_name,
            "total":    round(curr_analytics.categoryBreakdown[top_cat_name], 2),
        }

    # Month-over-month change
    change_amount = round(curr_total - prev_total, 2)
    change_pct    = round(((curr_total - prev_total) / prev_total) * 100, 1) if prev_total > 0 else None

    # Per-category comparison vs previous month
    all_cats = set(list(curr_analytics.categoryBreakdown.keys()) + list(prev_analytics.categoryBreakdown.keys()))
    category_changes = [
        {
            "category":  cat,
            "this_month": round(curr_analytics.categoryBreakdown.get(cat, 0), 2),
            "last_month": round(prev_analytics.categoryBreakdown.get(cat, 0), 2),
            "change":     round(
                curr_analytics.categoryBreakdown.get(cat, 0) -
                prev_analytics.categoryBreakdown.get(cat, 0), 2
            ),
        }
        for cat in sorted(all_cats)
    ]

    return jsonify({
        "month":            month,
        "prev_month":       prev_month,
        "curr_total":       curr_total,
        "prev_total":       prev_total,
        "change_amount":    change_amount,
        "change_pct":       change_pct,
        "top_category":     top_category,
        "category_changes": sorted(category_changes, key=lambda x: x["this_month"], reverse=True),
    }), 200


# ── Trends — monthly totals over time ────────────────────────────────────────
@analytics_bp.route("/trends", methods=["GET"])
def trends():
    """
    Covers: 'display spending trends'.
    Returns total spending per month across all time for the user.
    """
    uid = get_user_id()
    if not uid:
        return jsonify({"trends": {}}), 200

    all_expenses = Expense.query.filter_by(userID=uid).all()
    analytics    = Analytics(all_expenses)
    return jsonify({"trends": analytics.calculateTrends()}), 200


# ── Unusual Spending Detection ────────────────────────────────────────────────
@analytics_bp.route("/unusual", methods=["GET"])
def unusual_spending():
    """
    Covers: 'flag unusual spending compared to previous months'.
    Uses Analytics.detectAnomalies() — flags categories where this month's
    spending is 50%+ above the user's historical average for that category.
    Also auto-creates a Notification for any new flags found.
    """
    uid = get_user_id()
    if not uid:
        return jsonify({"flags": []}), 200

    all_expenses = Expense.query.filter_by(userID=uid).all()
    analytics    = Analytics(all_expenses)
    flags        = analytics.detectAnomalies(threshold=1.5)

    # Auto-notify for any new flags
    for flag in flags:
        msg = (
            f"Unusual spending in {flag['category']}: "
            f"${flag['current']} this month vs "
            f"${flag['average']} average ({flag['percent_over']}% over)"
        )
        existing = Notification.query.filter_by(userID=uid, message=msg).first()
        if not existing:
            notif = Notification(message=msg, userID=uid)
            notif.sendAlert()

    return jsonify({"flags": flags}), 200


# ── Spending Goals ────────────────────────────────────────────────────────────
@analytics_bp.route("/goals", methods=["GET"])
def get_goals():
    uid   = get_user_id()
    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))
    goals = SpendingGoal.query.filter_by(userID=uid, month=month).all()
    return jsonify([g.to_dict() for g in goals]), 200


@analytics_bp.route("/goals", methods=["POST"])
def set_goal():
    uid  = get_user_id()
    data = request.get_json()

    if not data.get("amountLimit") or not data.get("month"):
        return jsonify({"error": "amountLimit and month are required"}), 400

    try:
        amount_limit = float(data["amountLimit"])
        if amount_limit <= 0:
            return jsonify({"error": "amountLimit must be greater than 0"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amountLimit"}), 400

    # Update existing goal for that month + category, or create new
    existing = SpendingGoal.query.filter_by(
        userID=uid,
        month=data["month"],
        categoryID=data.get("categoryID"),
    ).first()

    if existing:
        existing.updateLimit(amount_limit)
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    goal = SpendingGoal(
        amountLimit=amount_limit,
        month=data["month"],
        categoryID=data.get("categoryID"),
        userID=uid,
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@analytics_bp.route("/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    uid  = get_user_id()
    goal = SpendingGoal.query.filter_by(goalID=goal_id, userID=uid).first()
    if not goal:
        return jsonify({"error": "Goal not found"}), 404
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Goal deleted"}), 200


# ── Monthly Reflections ───────────────────────────────────────────────────────
@analytics_bp.route("/reflections", methods=["GET"])
def get_reflections():
    uid   = get_user_id()
    month = request.args.get("month")
    query = Reflection.query.filter_by(userID=uid)
    if month:
        query = query.filter_by(month=month)
    return jsonify([r.to_dict() for r in query.order_by(Reflection.dateCreated.desc()).all()]), 200


@analytics_bp.route("/reflections", methods=["POST"])
def save_reflection():
    uid     = get_user_id()
    data    = request.get_json()
    month   = data.get("month", datetime.utcnow().strftime("%Y-%m"))
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "content is required"}), 400

    # One reflection per user per month — update if exists
    existing = Reflection.query.filter_by(userID=uid, month=month).first()
    if existing:
        existing.content = content
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    reflection = Reflection(month=month, content=content, userID=uid)
    reflection.saveNote()
    return jsonify(reflection.to_dict()), 201


# ── Notifications ─────────────────────────────────────────────────────────────
@analytics_bp.route("/notifications", methods=["GET"])
def get_notifications():
    uid    = get_user_id()
    notifs = Notification.query.filter_by(userID=uid).order_by(Notification.timestamp.desc()).all()
    return jsonify([n.to_dict() for n in notifs]), 200


@analytics_bp.route("/notifications/<int:alert_id>/read", methods=["PUT"])
def mark_read(alert_id):
    uid   = get_user_id()
    notif = Notification.query.filter_by(alertID=alert_id, userID=uid).first()
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    notif.markAsRead()
    return jsonify({"message": "Marked as read"}), 200