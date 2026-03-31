from database import db
from flask_login import UserMixin
from datetime import datetime


# ── User ──────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    userID       = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    passwordHash = db.Column(db.String(200), nullable=False)

    # Relationships
    profile  = db.relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    expenses = db.relationship("Expense", back_populates="user", cascade="all, delete-orphan")

    # Flask-Login requires a property named 'id'
    @property
    def id(self):
        return self.userID

    def __repr__(self):
        return f"<User {self.username}>"


# ── UserProfile ───────────────────────────────────────────────────────────────
class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id        = db.Column(db.Integer, primary_key=True)
    email     = db.Column(db.String(120), unique=True, nullable=False)
    firstName = db.Column(db.String(80), nullable=True)
    joinDate  = db.Column(db.Date, default=lambda: datetime.utcnow().date())

    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    user   = db.relationship("User", back_populates="profile")

    def updateProfile(self, data: dict):
        if "email" in data:
            self.email = data["email"]
        if "firstName" in data:
            self.firstName = data["firstName"]

    def getAccountSummary(self) -> dict:
        return {
            "username":  self.user.username,
            "email":     self.email,
            "firstName": self.firstName,
            "joinDate":  str(self.joinDate),
        }

    def __repr__(self):
        return f"<UserProfile {self.email}>"


# ── Category ──────────────────────────────────────────────────────────────────
class Category(db.Model):
    __tablename__ = "categories"

    categoryID = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(50), unique=True, nullable=False)
    colorCode  = db.Column(db.String(10), nullable=True)  # e.g. "#f4a261"

    expenses = db.relationship("Expense", back_populates="category")

    def getName(self) -> str:
        return self.name

    def updateCategory(self, name: str = None, colorCode: str = None):
        if name:
            self.name = name
        if colorCode:
            self.colorCode = colorCode

    def to_dict(self) -> dict:
        return {
            "categoryID": self.categoryID,
            "name":       self.name,
            "colorCode":  self.colorCode,
        }

    def __repr__(self):
        return f"<Category {self.name}>"


# ── Expense ───────────────────────────────────────────────────────────────────
class Expense(db.Model):
    __tablename__ = "expenses"

    expenseID   = db.Column(db.Integer, primary_key=True)
    amount      = db.Column(db.Float, nullable=False)
    date        = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    userID     = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    categoryID = db.Column(db.Integer, db.ForeignKey("categories.categoryID"), nullable=True)

    user     = db.relationship("User", back_populates="expenses")
    category = db.relationship("Category", back_populates="expenses")

    def edit(self, data: dict):
        if "amount" in data:
            self.amount = data["amount"]
        if "date" in data:
            self.date = data["date"]
        if "description" in data:
            self.description = data["description"]
        if "categoryID" in data:
            self.categoryID = data["categoryID"]

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def getDetails(self) -> dict:
        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "expenseID":    self.expenseID,
            "amount":       self.amount,
            "date":         str(self.date),
            "description":  self.description,
            "categoryID":   self.categoryID,
            "categoryName": self.category.name if self.category else None,
        }

    def __repr__(self):
        return f"<Expense ${self.amount} on {self.date}>"


# ── SpendingGoal ──────────────────────────────────────────────────────────────
class SpendingGoal(db.Model):
    __tablename__ = "spending_goals"

    goalID      = db.Column(db.Integer, primary_key=True)
    amountLimit = db.Column(db.Float, nullable=False)
    month       = db.Column(db.String(7), nullable=False)  # "YYYY-MM"

    userID     = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    categoryID = db.Column(db.Integer, db.ForeignKey("categories.categoryID"), nullable=True)

    user     = db.relationship("User")
    category = db.relationship("Category")

    def checkProgress(self) -> float:
        """Returns total spent this month in this category."""
        year, mon = map(int, self.month.split("-"))
        expenses = Expense.query.filter(
            Expense.userID == self.userID,
            Expense.categoryID == self.categoryID,
            db.extract("year", Expense.date) == year,
            db.extract("month", Expense.date) == mon,
        ).all()
        return round(sum(e.amount for e in expenses), 2)

    def updateLimit(self, new_limit: float):
        self.amountLimit = new_limit

    def to_dict(self) -> dict:
        spent = self.checkProgress()
        return {
            "goalID":       self.goalID,
            "amountLimit":  self.amountLimit,
            "month":        self.month,
            "categoryID":   self.categoryID,
            "categoryName": self.category.name if self.category else None,
            "spent":        spent,
            "remaining":    round(self.amountLimit - spent, 2),
        }

    def __repr__(self):
        return f"<SpendingGoal {self.month} ${self.amountLimit}>"


# ── Reflection ────────────────────────────────────────────────────────────────
class Reflection(db.Model):
    __tablename__ = "reflections"

    noteID      = db.Column(db.Integer, primary_key=True)
    month       = db.Column(db.String(7), nullable=False)  # "YYYY-MM"
    content     = db.Column(db.Text, nullable=False)
    dateCreated = db.Column(db.DateTime, default=datetime.utcnow)

    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    user   = db.relationship("User")

    def saveNote(self):
        db.session.add(self)
        db.session.commit()

    def getMonthlyReflection(self) -> str:
        return self.content

    def to_dict(self) -> dict:
        return {
            "noteID":      self.noteID,
            "month":       self.month,
            "content":     self.content,
            "dateCreated": str(self.dateCreated),
        }

    def __repr__(self):
        return f"<Reflection {self.month}>"


# ── Notification ──────────────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = "notifications"

    alertID   = db.Column(db.Integer, primary_key=True)
    message   = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    isRead    = db.Column(db.Boolean, default=False)

    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    user   = db.relationship("User")

    def sendAlert(self):
        db.session.add(self)
        db.session.commit()

    def markAsRead(self):
        self.isRead = True
        db.session.commit()

    def to_dict(self) -> dict:
        return {
            "alertID":   self.alertID,
            "message":   self.message,
            "timestamp": str(self.timestamp),
            "isRead":    self.isRead,
        }

    def __repr__(self):
        return f"<Notification {self.alertID}>"


# ── Analytics (stateless helper — not a DB table) ─────────────────────────────
class Analytics:
    """
    Mirrors the Analytics class from the UML diagram.
    Operates on a list of Expense objects passed in.
    """

    def __init__(self, expenses: list):
        self.expenses    = expenses
        self.totalSpent  = round(sum(e.amount for e in expenses), 2)
        self.categoryBreakdown = self._build_breakdown()

    def _build_breakdown(self) -> dict:
        breakdown = {}
        for e in self.expenses:
            name = e.category.name if e.category else "Uncategorized"
            breakdown[name] = round(breakdown.get(name, 0) + e.amount, 2)
        return breakdown

    def calculateTrends(self) -> dict:
        """Groups total spending by month."""
        from collections import defaultdict
        trends = defaultdict(float)
        for e in self.expenses:
            key = str(e.date)[:7]  # "YYYY-MM"
            trends[key] = round(trends[key] + e.amount, 2)
        return dict(sorted(trends.items()))

    def detectAnomalies(self, threshold: float = 1.5) -> list:
        """
        Flags categories where this month's spending exceeds
        the user's historical average by the given multiplier threshold.
        Returns a list of flag dicts.
        """
        from collections import defaultdict
        monthly = defaultdict(lambda: defaultdict(float))
        for e in self.expenses:
            month = str(e.date)[:7]
            cat   = e.category.name if e.category else "Uncategorized"
            monthly[month][cat] += e.amount

        if not monthly:
            return []

        current_month = max(monthly.keys())
        past_months   = {m: v for m, v in monthly.items() if m != current_month}

        if not past_months:
            return []

        # Average per category across past months
        cat_totals = defaultdict(list)
        for month_data in past_months.values():
            for cat, total in month_data.items():
                cat_totals[cat].append(total)

        averages = {cat: sum(vals) / len(vals) for cat, vals in cat_totals.items()}

        flags = []
        for cat, current_total in monthly[current_month].items():
            avg = averages.get(cat)
            if avg and current_total > avg * threshold:
                pct_over = round(((current_total - avg) / avg) * 100, 1)
                flags.append({
                    "category":    cat,
                    "average":     round(avg, 2),
                    "current":     round(current_total, 2),
                    "percent_over": pct_over,
                })

        return flags


# ── Report (stateless helper — not a DB table) ────────────────────────────────
class Report:
    """
    Mirrors the Report class from the UML diagram.
    Generates CSV output from a list of Expense objects.
    """

    def __init__(self, expenses: list, file_format: str = "csv"):
        self.expenses      = expenses
        self.fileFormat    = file_format
        self.generatedDate = datetime.utcnow().date()

    def generateCSV(self) -> str:
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ExpenseID", "Date", "Category", "Amount", "Description"])
        for e in self.expenses:
            writer.writerow([
                e.expenseID,
                e.date,
                e.category.name if e.category else "",
                e.amount,
                e.description or "",
            ])
        output.seek(0)
        return output.getvalue()

    def download(self):
        """Called by the route to return a Flask Response."""
        from flask import Response
        return Response(
            self.generateCSV(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )