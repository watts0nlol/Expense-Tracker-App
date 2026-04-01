"""
Run this once after app.py to seed the default categories into the database.
  python seed_categories.py
"""
from app import app
from database import db
from models import Category

DEFAULT_CATEGORIES = [
    {"name": "Food & Dining",  "colorCode": "#f4a261"},
    {"name": "Transport",      "colorCode": "#2a9d8f"},
    {"name": "Shopping",       "colorCode": "#e76f51"},
    {"name": "Entertainment",  "colorCode": "#a8dadc"},
    {"name": "Health",         "colorCode": "#e63946"},
    {"name": "Housing",        "colorCode": "#457b9d"},
    {"name": "Utilities",      "colorCode": "#6d6875"},
    {"name": "Other",          "colorCode": "#b5b5b5"},
]

with app.app_context():
    for cat_data in DEFAULT_CATEGORIES:
        exists = Category.query.filter_by(name=cat_data["name"]).first()
        if not exists:
            cat = Category(name=cat_data["name"], colorCode=cat_data["colorCode"])
            db.session.add(cat)
    db.session.commit()
    print("Categories seeded successfully.")
