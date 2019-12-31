import os
import datetime
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, clean_db, str_to_date

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
@login_required
def index():
    clean_db(session["user_id"])

    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()

    query = cursor.execute("SELECT * FROM assignments WHERE user_id = :user_id", {"user_id": session["user_id"]})
    rows = query.fetchall()

    dates = []
    for row in rows:
        dates.append(row[4])
    dates.sort()

    assignments = []
    descriptions = []
    for date in dates:
        for row in rows:
            if date == row[4] and row[2] not in assignments:
                assignments.append(row[2])
                descriptions.append(row[3])
                break

    return render_template("index.html", dates=dates, assignments=assignments, descriptions=descriptions, len=len(assignments))


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username")
        elif not request.form.get("password"):
            return apology("must provide password")

        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        query = cursor.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")})
        ans = query.fetchone()

        if not ans:
            return apology("User does not exist")
        elif not check_password_hash(ans[2], request.form.get("password")):
            return apology("User does not exist")

        session["user_id"] = ans[0]

        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username")
        elif not request.form.get("password"):
            return apology("must provide password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password fields do not match")

        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        query = cursor.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")})
        ans = query.fetchone()

        if ans:
            return apology("username already exists")

        pw_hash = generate_password_hash(request.form.get("password"))

        cursor.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username": request.form.get("username"), "hash": pw_hash})
        conn.commit()

        return render_template("login.html")
    else:
        return render_template("register.html")


@app.route("/create_assignment", methods=["GET", "POST"])
@login_required
def create_assignment():
    if request.method == "POST":
        if not request.form.get("assignment_name"):
            return apology("must provide an assignment name")
        elif not request.form.get("deadline"):
            return apology("must provide a due date for the assignment")

        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        query = cursor.execute("SELECT * FROM assignments WHERE assignment_name = :assignment_name AND user_id = :user_id",
            {"assignment_name": request.form.get("assignment_name"), "user_id": session["user_id"]})
        ans = query.fetchone()

        if ans:
            return apology("you already have an assignment with that name")

        if request.form.get("description"):
            values = {
                "user_id": session["user_id"],
                "assignment_name": request.form.get("assignment_name"),
                "description": request.form.get("description"),
                "deadline": request.form.get("deadline")
                }
            cursor.execute("INSERT INTO assignments (user_id, assignment_name, description, deadline) VALUES (:user_id, :assignment_name, :description, :deadline)", values)
        else:
            values = {"user_id": session["user_id"], "assignment_name": request.form.get("assignment_name"), "deadline": request.form.get("deadline")}
            cursor.execute("INSERT INTO assignments (user_id, assignment_name, deadline) VALUES (:user_id, :assignment_name, :deadline)", values)
        conn.commit()

        return redirect("/")
    else:
        return render_template("create_assignment.html", current_date=str(datetime.date.today()))


@app.route("/delete_assignment", methods=["GET", "POST"])
@login_required
def delete_assignment():
    if request.method == "POST":
        if not request.form.getlist("assignment_names"):
            return apology("must provide an assignment name")

        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        for assignment_name in request.form.getlist("assignment_names"):
            query = cursor.execute("SELECT * FROM assignments WHERE assignment_name = :assignment_name AND user_id = :user_id",
                {"assignment_name": assignment_name, "user_id": session["user_id"]})
            ans = query.fetchone()

            if not ans:
                return apology("you do not have an assignment called {}".format(assignment_name))

            cursor.execute("DELETE FROM assignments WHERE assignment_name = :assignment_name AND user_id = :user_id",
                {"assignment_name": assignment_name, "user_id": session["user_id"]})

        conn.commit()

        return render_template("deleted_assignment.html", deleted=request.form.getlist("assignment_names"))
    else:
        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        query = cursor.execute("SELECT * FROM assignments WHERE user_id = :user_id", {"user_id": session["user_id"]})
        rows = query.fetchall()

        assignments = []
        for row in rows:
            assignments.append(row[2])

        return render_template("delete_assignment.html", assignments=assignments)


# @app.route("/select_assignment", methods=["GET"])
# @login_required
# def select_assignment():
#     conn = sqlite3.connect("planner.db")
#     cursor = conn.cursor()
#
#     query = cursor.execute("SELECT * FROM assignments WHERE user_id = :user_id", {"user_id": session["user_id"]})
#     rows = query.fetchall()
#
#     assignments = []
#     for row in rows:
#         assignments.append(row[2])
#
#     return render_template("select_assignment.html", assignments=assignments)
#
#
# @app.route("/edit_assignment", methods=["GET", "POST"])
# @login_required
# def edit_assignment():
#     if request.method == "POST":
#         pass
#     else:
#         return request.form.get("assignment_name")


def errorhandler(e):
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
