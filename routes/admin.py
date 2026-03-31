from flask import Blueprint, jsonify
from models import User
from database import db
import os, shutil, datetime

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
def list_users():
    users = User.query.all()
    return jsonify([
        {
            "userID":    u.userID,
            "username":  u.username,
            "email":     u.profile.email if u.profile else None,
            "firstName": u.profile.firstName if u.profile else None,
            "joinDate":  str(u.profile.joinDate) if u.profile else None,
        }
        for u in users
    ]), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {user_id} deleted"}), 200


@admin_bp.route("/backup", methods=["POST"])
def backup_database():
    db_path = os.path.join("instance", "expenses.db")
    if not os.path.exists(db_path):
        return jsonify({"error": "Database file not found"}), 404

    timestamp   = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"expenses_backup_{timestamp}.db"
    backup_path = os.path.join("instance", backup_name)
    shutil.copy2(db_path, backup_path)

    return jsonify({"message": "Backup created", "backup_file": backup_name}), 200