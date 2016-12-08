from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from werkzeug.utils import secure_filename

from helpers import *
"""
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime
"""
""" Google Calendar Stuff """
"""
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

"""
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'List It!'

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///listit.db")

@app.route("/")
def index():
    """Show current portfolio"""

    # render, providing jinja with data
    return render_template("index.html")
    
@app.route("/view")
def view():
    # render
    return render_template("view.html")
    
@app.route("/addevent", methods=["GET", "POST"])
def addevent():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # ensure something was submitted
        if not request.form.get("name") or not request.form.get("type"):
            return apology("")

        event = {
          'summary': 'Google I/O 2015',
          'location': '800 Howard St., San Francisco, CA 94103',
          'description': 'A chance to hear more about Google\'s developer products.',
          'start': {
            'dateTime': '2015-05-28T09:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
          },
          'end': {
            'dateTime': '2015-05-28T17:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
          },
          'recurrence': [
            'RRULE:FREQ=DAILY;COUNT=2'
          ],
          'attendees': [
            {'email': 'lpage@example.com'},
            {'email': 'sbrin@example.com'},
          ],
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'email', 'minutes': 24 * 60},
              {'method': 'popup', 'minutes': 10},
            ],
          },
        }
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        # print 'Event created: %s' % (event.get('htmlLink'))
        
        """Register!"""
        
        # add event to sql
        db.execute("""INSERT INTO events(name, type, 
        start, end, description, link, photo, eventid, orgid)
            VALUES(:name, :type, :start, :end, :description, :link, :photo, :eventid, :orgid)""",
            name = request.form.get("name"),
            type = request.form.get("type"),
            start = request.form.get("start"),
            end = request.form.get("end"),
            description = request.form.get("description"),
            link = request.form.get("link"),
            photo = request.form.get("photo"),
            eventid = "hello",
            orgid = orgid)
        
        # redirect user to home page
        return redirect(url_for("viewevent"))
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("addevent.html")

@app.route("/viewevent")
def viewevent():

    event = db.execute("""SELECT *
                        FROM events
                        WHERE id = :id""", id=eventid) 
    return render_template("viewevent.html", event = events)

@app.route("/history")
@login_required
    return render_template("viewevent.html", event = eve)
    """Show history of transactions."""
    
    # store table from purchases for this user
    if db.execute("SELECT * FROM sqlite_master WHERE name ='purchases' and type='table'"):
        logs = db.execute("""SELECT transacted, symbol, price, shares
                        FROM 'purchases'
                        WHERE user = :id""", id=session["user_id"]) 
        return render_template("history.html", logs=logs)
    # render, providing jinja with data
    return render_template("history.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        
        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")
        
        # remember which user has logged in
        session["user_id"] = rows[0]["id"]
        
        # redirect user to home page
        return redirect(url_for("index"))
        
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
        
@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # forget any user_id
    session.clear()
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        """Checks!"""
        
        # ensure first and last name were submitted
        if not request.form.get("firstname"):
            return apology("This field is required")
        
        if not request.form.get("lastname"):
            return apology("This field is required")
            
        # ensure username was submitted
        if not request.form.get("username"):
            return apology("This field if required")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("This field is required")

        # ensure passwords are the same
        elif request.form.get("password") != request.form.get("confirm_password"):
            return apology("passwords don't match")
        
        """Register!"""
        

        studorg = db.execute("SELECT id FROM organizations WHERE name = :name", name = request.form.get("student_org"))
        # add user into table of users
        session["user_id"] = db.execute("""INSERT INTO users(first, last, 
        username, password, huid, orgid)
            VALUES(:first, :last, :username, :hash, :huid, :orgid)""",
            first = request.form.get("firstname"),
            last = request.form.get("lastname"),
            username=request.form.get("username"),
            hash=pwd_context.encrypt(request.form.get("password"),
            huid = request.form.get("huid"),
            orgid = studorg))
    
        # remember which user has logged in
        tmp = db.execute("SELECT MAX(id) as max FROM 'users'")
        session["user_id"] = tmp[0]["max"]
        
        # remember which user has logged in
        tmp = db.execute("SELECT MAX(orgid) as max FROM 'users'")
        session["org_id"] = tmp[0]["max"]
        
        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        orgs = db.execute("SELECT name FROM organizations") 
        return render_template("register.html", orgs=orgs)
        
@app.route("/changepass", methods=["GET", "POST"])
@login_required
def changepass():
    """Change Password"""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # ensure username was submitted
        if not request.form.get("passwordOld"):
            return apology("must provide old password")
        
        # ensure password was submitted
        elif not request.form.get("passwordNew"):
            return apology("must provide new password")

        # ensure passwords are the same
        elif request.form.get("passwordNew") != request.form.get("passwordCheck"):
            return apology("passwords don't match")

        # query database for username
        rows = db.execute("SELECT hash FROM users WHERE id = :id", id=session["user_id"])
        
        # ensure username exists and password is correct
        if not pwd_context.verify(request.form.get("passwordOld"), rows[0]["hash"]):
            return apology("old password incorect")
        
        db.execute("""UPDATE users
                    SET hash = :hash
                    WHERE id = :id""",
                    hash = pwd_context.encrypt(request.form.get("passwordNew")),
                    id = session["user_id"])
                    
        return redirect(url_for("index"))
        
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("changepass.html")