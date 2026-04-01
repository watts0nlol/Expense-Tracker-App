from flask import Flask, render_template
from flask_login import LoginManager
from flask_cors import CORS
from dotenv import load_dotenv
from database import init_db, db
from models import User
from routes.auth import auth_bp, bcrypt
from routes.expenses import expenses_bp
from routes.analytics import analytics_bp
from routes.admin import admin_bp
import os

load_dotenv()

app = Flask(__name__)

#  Config 
app.config["SECRET_KEY"]                     = os.getenv("SECRET_KEY", "fallback-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"]        = os.getenv("DATABASE_URL", "sqlite:///expenses.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#  Extensions 
CORS(app)
bcrypt.init_app(app)

#  Database 
init_db(app)

#  Login Manager (still set up so login/logout work, but not enforced on pages) 
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    # Return JSON instead of redirecting so API calls don't break
    return {"error": "Not logged in"}, 401

#  API Blueprints 
app.register_blueprint(auth_bp,      url_prefix="/auth")
app.register_blueprint(expenses_bp,  url_prefix="/expenses")
app.register_blueprint(analytics_bp, url_prefix="/analytics")
app.register_blueprint(admin_bp,     url_prefix="/admin")

#  Page Routes (no auth required) 
@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/expenses-page")
def expenses_page():
    return render_template("expenses.html")

@app.route("/analytics-page")
def analytics_page():
    return render_template("analytics.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/logout-page")
def logout_page():
    return render_template("logout.html")


if __name__ == "__main__":
    app.run(debug=True)