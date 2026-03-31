from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import User, UserProfile
from database import db
from datetime import datetime

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()


@auth_bp.route("/register", methods=["POST"])
def register():
    data      = request.get_json()
    username  = data.get("username", "").strip()
    email     = data.get("email", "").strip()
    password  = data.get("password", "")
    firstName = data.get("firstName", "").strip()

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400

    if UserProfile.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    try:
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, passwordHash=hashed_pw)
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(
            email=email,
            firstName=firstName,
            joinDate=datetime.utcnow().date(),
            userID=user.userID,
        )
        db.session.add(profile)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

    return jsonify({"message": "Account registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if not user or not bcrypt.check_password_hash(user.passwordHash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user)
    return jsonify({"message": "Logged in successfully", "username": user.username}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    if not current_user.is_authenticated:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(current_user.profile.getAccountSummary()), 200


@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
    if not current_user.is_authenticated:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    current_user.profile.updateProfile(data)
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200