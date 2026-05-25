# Expense Tracker

A simple web app to track personal expenses with categories, monthly summaries, and spending breakdowns.

## Features

- Add expenses with amount, description, category, date, and optional receipt image
- View and filter expenses by month and category
- Monthly totals and category breakdown chart
- Delete expenses
- Attach receipt images (PNG, JPG, GIF, WebP, max 5 MB)
- Export all expenses to Excel (.xlsx)
- Data stored locally in SQLite (`expenses.db`); receipts in `uploads/receipts/`

## Requirements

- Python 3.10+

## Setup

```bash
cd ExpenseTracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Tests

```bash
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\pytest -v
```

## Project structure

```
ExpenseTracker/
├── app.py           # Flask app and API routes
├── database.py      # SQLite helpers
├── receipts.py      # Receipt image upload helpers
├── requirements.txt
├── expenses.db      # Created on first run
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/expenses?month=YYYY-MM&category=Food` | List expenses |
| POST | `/api/expenses` | Add expense (multipart form; optional `receipt` file) |
| DELETE | `/api/expenses/<id>` | Delete expense |
| GET | `/api/summary?month=YYYY-MM` | Monthly summary |
| GET | `/api/expenses/export` | Download all expenses as Excel |
