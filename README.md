# Personal Expense Tracker

Our web-based expense tracking application built with Flask and SQLite. It is designed to make sure you are keep tracking of where your money is going!

## Requirements

- Python 3.9 or higher
- pip


## Setup

1. Clone the repository in VSCode or on whatever software you are using and go to the project folder.

2. Install all dependencies by running: pip install -r requirements.txt
  
3. To access the categories in the expense tracker, run in terminal: python seed_categories.py. When resetting the app, make sure to delete expenses.db under instances and rerun this before starting app.py.

4. Start the app by running: python app.py

5. Open your browser and go to: http://127.0.0.1:5000

6. Register / Log in in the login page

7. Start tracking your spending! Everything is ready to go.

## First Use

Go to http://127.0.0.1:5000/register and create an account, then log in at /login. From there you can start adding expenses on the Dashboard.

## Pages

- /dashboard — Add expenses and view your monthly summary
- /expenses-page — View, filter, edit, delete, and export your expenses
- /analytics-page — Spending insights, trends, goals, reflections, and unusual spending detection
- /login — Log in to your account
- /register — Create a new account
- /logout — Log out

## Notes

- The instance folder and .env file are not included in the repository for security reasons
- Unusual spending detection requires at least 2 months of recorded expenses to compare against
- CSV export is available on the Expenses page and can be filtered by month
