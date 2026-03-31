from flask_sqlalchemy import SQLAlchemy

# This db instance will be imported by models.py and app.py
db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)

    with app.app_context():
        db.create_all()  # Creates all tables if they don't exist