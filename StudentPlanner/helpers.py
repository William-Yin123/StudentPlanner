import os
import datetime
import sqlite3
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"), ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def str_to_date(str_date):
    params = str_date.split("-")
    for i in range(len(params)):
        params[i] = int(params[i])
    return datetime.date(params[0], params[1], params[2])


def clean_db(user_id):
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()

    query = cursor.execute("SELECT * FROM assignments WHERE user_id = :user_id", {"user_id": user_id})
    rows = query.fetchall()

    today = datetime.date.today()
    dates = []
    for row in rows:
        date = str_to_date(row[4])
        if today > date and row[4] not in dates:
            cursor.execute("DELETE FROM assignments WHERE deadline = :date AND user_id = :user_id", {"date": row[4], "user_id": user_id})
            dates.append(row[4])
            conn.commit()
