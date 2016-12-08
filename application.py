from cs50 import SQL
import re
from flask import Flask, jsonify, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from werkzeug.utils import secure_filename
import os
import validators
from datetime import datetime, date
from helpers import *

# http://stewartjpark.com/Flask-JSGlue/
from flask_jsglue import JSGlue

# Google Calendar Stuff
# https://developers.google.com/api-client-library/python/auth/web-app
# https://developers.google.com/google-apps/calendar/quickstart/python
import json
import httplib2
import uuid
from apiclient import discovery
from oauth2client import client

# uploading images
UPLOAD_FOLDER = '/home/ubuntu/workspace/finalProject/static/uploaded'

# configure application
app = Flask(__name__)
# necessary for JS calendar, see viewcal.html for more info/implementation
JSGlue(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = str(uuid.uuid4())

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

# Get Google API credentials, as shown on https://developers.google.com/api-client-library/python/auth/web-app
@app.route('/oauth2callback')
def oauth2callback():
  flow = client.flow_from_clientsecrets(
      'client_secret.json',
      scope='https://www.googleapis.com/auth/calendar',
      redirect_uri=url_for('oauth2callback', _external=True))
  if 'code' not in request.args:
    auth_uri = flow.step1_get_authorize_url()
    return redirect(auth_uri)
  else:
    auth_code = request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    session['credentials'] = credentials.to_json()
    return redirect(url_for('googlecal'))

@app.route("/")
def index():
    return render_template("index.html")
    
@app.route("/viewcal")
def viewcal():
    # all calendar data is passed via events(below) to JS through JSON
    return render_template("viewcal.html")

# used for viewcal to render events from JSON format
@app.route("/events")
def events():
    events = db.execute("SELECT * FROM events")
    # json format
    events = [{"title": item["name"],
                "url": url_for('viewevent', event_id=item["id"]),
                "start": item["startdate"] + "T" + item["starttime"] + ":00-05:00",
                "end": item["enddate"] + "T" + item["endtime"] + ":00-05:00"
                } for item in events]
    # return jsonified event listings
    return jsonify(events)
    
@app.route("/addevent", methods=["GET", "POST"])
@login_required
def addevent():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        """ error checks """
        
        # check for all fields existing, using helper function required_info
        fields = [["name", "Name"], ["startdate", "Start Date"],
                ["enddate", "End Date"], ["starttime", "Start Time"],
                ["endtime", "End Time"]]
        if not required_info(fields):
            return render_template("addevent.html")
        
        # check event type
        if request.form.get("type") == "--Select an Event Type--":
            flash('Must Select An Event Type')
            return render_template("addevent.html")
        
        # check dates
        if not check_dates(request.form.get("startdate"), request.form.get("enddate"), request.form.get("starttime"), request.form.get("endtime")):
            return render_template("addevent.html")
        
        # upload image, if there is one. If not, NULL is stored
        # http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
        filename = "NULL"
        if 'file' in request.files:
            file = request.files['file']
            # if user does not select file, browser also submit a empty part without filename
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        photo = filename
                    
        # add event to sql
        db.execute("""INSERT INTO events(name, type, 
        startdate, enddate, description, link, photo, eventid, orgid, location, starttime, endtime)
            VALUES(:name, :type, :startdate, :enddate, :description, :link, :photo, :eventid, :orgid, :location, :starttime, :endtime)""",
            name = request.form.get("name"),
            type = request.form.get("type"),
            startdate = request.form.get("startdate"),
            enddate = request.form.get("enddate"),
            description = request.form.get("description"),
            link = request.form.get("link"),
            photo = photo,
            eventid = "hello",
            orgid = session["org_id"],
            location = request.form.get("location"),
            starttime = request.form.get("starttime"),
            endtime = request.form.get("endtime"))
        
        # remember which event is being displayed
        tmp = db.execute("SELECT MAX(id) as max FROM events")
        session["event_id"] = tmp[0]["max"]
        
        # redirect user to see the event
        return redirect(url_for('viewevent', event_id=session["event_id"]))
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        session["event_id"] = None
        return render_template("addevent.html")

@app.route("/viewevent/<event_id>", methods=["GET", "POST"])
def viewevent(event_id):
    
    # on the vievent page, users can select to edit, delete, or add to google cal. redirect accordingly
    if request.method == "POST":
        if "googlecal" in request.form:
            return redirect(url_for("googlecal"))
        if "edit" in request.form:
            return redirect(url_for("editevent"))
        else:
            return redirect(url_for("delete"))
    else:
        event = db.execute("""SELECT *
                            FROM events
                            WHERE id = :id""", id=event_id)
        session['event_id'] = event_id
                            
        # convert dates and times to more readable format, with constructed helper function
        event = convert_datetime(event)
        event = event[0]
        
        # find out if user is logged in, and if so, if the event is associated with their organization
        if not session.get("org_id"):
            editable = False
        elif session.get("org_id") == event["orgid"]:
            editable = True
        else:
            editable = False
        
        return render_template("viewevent.html", event = event, editable = editable)
    
@app.route("/viewevents", methods=["GET", "POST"])
@login_required
def viewevents():
    
    # allow for viewing single events, editing them, and deleting them
    if request.method == "POST":
        
        if "view" in request.form:
            session["event_id"] = int(request.form['view'])
            return redirect(url_for('viewevent', event_id=session["event_id"]))
        elif "edit" in request.form:
            session["event_id"] = int(request.form['edit'])
            return redirect(url_for("editevent"))
        else:
            session["event_id"] = int(request.form['delete'])
            return redirect(url_for("delete"))
    else:
        
        # grab events from current student org 
        events = db.execute("""SELECT *
                            FROM events
                            WHERE orgid = :orgid
                            ORDER BY startdate""", orgid=session["org_id"])
            
        # deal with a group that has no listed events
        if not events:
            flash('You have no listed events!')
            noevents = True;
        else:
            noevents = False;
        
        # convert times and descriptions, make more readable
        events = convert_datetime(events)
        events = shorten_description(events)
    
        return render_template("viewevents.html", events = events)
    
@app.route("/delete")
@login_required
@event_required
def delete():
    
    event = db.execute("SELECT name, photo FROM events WHERE id = :id", id = session["event_id"])
    
    # remove photo if there was one
    oldphoto = event[0]["photo"]
    if oldphoto != "NULL":
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], oldphoto))
    
    # grab name to be shown on deleted page
    name = event[0]["name"]
    db.execute("DELETE FROM events WHERE id = :id", id = session["event_id"])
    
    # clear the current selected event
    session["event_id"] = None
    
    return render_template("delete.html", name = name)
    
@app.route("/login", methods=["GET", "POST"])
def login():
    # standard method, very similar to PSET 7
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # checks
        fields = [["username", "User Name"], ["password", "Password"]]
        if not required_info(fields):
            return render_template("login.html")
            
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        
        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["password"]):
            flash('Incorrect Username/Password')
            return render_template("login.html")
    
        # remember which user has logged in, and with what organization
        session["user_id"] = rows[0]["id"]
        session["org_id"] = rows[0]["orgid"]
    
        # redirect user to home page
        return redirect(url_for("index"))
        
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
@app.route("/forgotuser", methods=["GET", "POST"])
def forgotuser():
    # This is is a demonstration of how a forgot username/passord(below) function would work
    # obviously not the most secure method, further integration with HarvardKey necessary is a next step
    if request.method == "POST":
        
        # checks
        fields = [["firstname", "First Name"], ["lastname", "Last Name"], ["huid", "HUID"]]
        if not required_info(fields):
            return render_template("forgotuser.html")
        
        rows = db.execute("SELECT * FROM users WHERE huid = :huid", huid=request.form.get("huid"))
        
        if not rows:
            flash('This account does not exist')
            return render_template("forgotuser.html")
        if (rows[0]["first"]!=request.form.get("firstname")) or (rows[0]["last"]!=request.form.get("lastname")):
            flash('Incorrect First Name/Last Name')
            return render_template("forgotuser.html")
            
        # show username, if user has given correct huid and first and last name
        username = rows[0]["username"]
        return render_template("username.html", username = username)
            
    else:
        return render_template("forgotuser.html")
    
@app.route("/resetpass", methods=["GET", "POST"])
def resetpass():
    """Reset Password"""
    if request.method == "POST":
        # same notes as with forgotuser function above
        # checks
        fields = [["username", "Username"], ["huid", "HUID"]]
        if not required_info(fields):
            return render_template("resetpass.html")
        rows = db.execute("SELECT * FROM users WHERE huid = :huid", huid=request.form.get("huid"))
        
        if not rows:
            flash('This account does not exist')
            return render_template("resetpass.html")
        
        if (rows[0]["username"]!=request.form.get("username")):
            flash('Incorrect Username/HUID')
            return render_template("resetpass.html")
        
        elif request.form.get("password") != request.form.get("confirm_password"):
            flash('Passwords Do Not Match')
            return render_template("resetpass.html")
        
        # update with new password
        db.execute("""UPDATE users
                SET password = :password
                WHERE huid = :huid""",
                password = pwd_context.encrypt(request.form.get("password")),
                huid = request.form.get("huid"))
        return render_template("password.html", password = password)
        
    else:
        return render_template("resetpass.html")

@app.route("/logout")
def logout():
    """Log user out."""
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
        
        # checks
        fields = [["firstname", "First Name"], ["lastname", "Last Name"],
                ["username", "User Name"], ["password", "Password"],
                ["huid", "HUID"]]
        if not required_info(fields):
            organizations = db.execute("SELECT name FROM organizations") 
            return render_template("register.html", organizations = organizations)
        
        # check if it's an HUID (8 characters)
        elif len(request.form.get("huid")) < 8:
            flash('Must Provide A Valid HUID')
            organizations = db.execute("SELECT name FROM organizations") 
            return render_template("register.html", organizations=organizations)
        
        # make sure an organization is selected
        elif request.form.get("student_org") == "--Select an Organization--":
            flash('Must Select An Organization')
            organizations = db.execute("SELECT name FROM organizations") 
            return render_template("register.html", organizations=organizations)

        # ensure passwords are the same
        elif request.form.get("password") != request.form.get("confirm_password"):
            flash('Passwords Do Not Match')
            organizations = db.execute("SELECT name FROM organizations") 
            return render_template("register.html", organizations=organizations)
        
        # check if proposed user is in the harvard facebook
        first = "%" + request.form.get("firstname") + "%"
        last = "%" + request.form.get("lastname") + "%"
        name_check = db.execute("SELECT * FROM names WHERE first LIKE :first AND last LIKE :last",
                            first = first, last = last)
        if not name_check:
            flash('Please Input Your Name, as Listed on the Harvard Facebook')
            organizations = db.execute("SELECT name FROM organizations") 
            return render_template("register.html", organizations=organizations)
        
        # register user
        orgid = db.execute("SELECT id FROM organizations WHERE name = :name", name = request.form.get("student_org"))
        session["org_id"] = orgid[0]["id"]
        # add user into table of users
        db.execute("""INSERT INTO users(first, last, username, password, huid, orgid)
            VALUES(:first, :last, :username, :password, :huid, :orgid)""",
            first = request.form.get("firstname"),
            last = request.form.get("lastname"),
            username = request.form.get("username"),
            password = pwd_context.encrypt(request.form.get("password")),
            huid = request.form.get("huid"),
            orgid = session["org_id"])
        
        # remember which user has logged in
        tmp = db.execute("SELECT MAX(id) as max FROM users")
        session["user_id"] = tmp[0]["max"]
        
        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        # must load up list of organizations to be displayed in dropdown
        organizations = db.execute("SELECT name FROM organizations") 
        return render_template("register.html", organizations=organizations)
        
@app.route("/changepass", methods=["GET", "POST"])
@login_required
def changepass():
    """Change Password"""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # checks
        fields = [["passwordOld", "Old Password"], ["passwordNew", "New Password"],
                ["passwordCheck", "New Password Twice"]]
        if not required_info(fields):
            return render_template("changepass.html")
        
        # ensure passwords are the same
        elif request.form.get("passwordNew") != request.form.get("passwordCheck"):
            flash('Passwords Do Not Match')
            return render_template("changepass.html")
        
        # query database for username
        rows = db.execute("SELECT password FROM users WHERE id = :id", id=session["user_id"])
        
        # ensure username exists and password is correct
        if not pwd_context.verify(request.form.get("passwordOld"), rows[0]["password"]):
            flash('Old Password Incorrect')
            return render_template("changepass.html")
        
        # change password
        db.execute("""UPDATE users
                    SET password = :password
                    WHERE id = :id""",
                    password = pwd_context.encrypt(request.form.get("passwordNew")),
                    id = session["user_id"])
        return redirect(url_for("index"))
        
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("changepass.html")
        
@app.route("/search", methods=["GET", "POST"])
def search():
    """Search for Event"""
    
    if request.method == 'POST':
        
        # check each of the fields
        if not request.form.get("name"):
            name = "%"
        else:
            name = "%" + request.form.get("name") + "%"
            
        if not request.form.get("location"):
            location = "%"
        else:
            location = "%" + request.form.get("location") + "%"
        
        if request.form.get("type") == "--Select an Event Type--":
            type = "%"
        else:
            type = "%" + request.form.get("type") + "%"
        
        # if we're dealing without a date
        if not request.form.get("date"):
            events = db.execute("""SELECT * FROM events WHERE name LIKE :name AND type LIKE :type AND location LIKE :location ORDER BY startdate""",
                            name = name, type = type, location = location)
        # if we're dealing with a date
        else: 
            events = db.execute("""SELECT * FROM events WHERE name LIKE :name AND type LIKE :type AND location LIKE :location
                            AND (startdate = :date or enddate = :date) ORDER BY startdate""",
                            name = name, type = type, location = location, date = request.form.get("date"))
            
        # convert times and descriptions, make more readable
        events = convert_datetime(events)
        events = shorten_description(events)
        session["events"] = events
        
        # show user the results
        return redirect(url_for("searchresults"))
        
    else:
        return render_template("search.html")
        
@app.route("/searchresults", methods=["GET", "POST"])
def searchresults():
    """Display search results"""
    
    if request.method == "POST":
        # user can click on events, like viewevents without editing/deleting options
        session["event_id"] = int(request.form['view'])
        return redirect(url_for('viewevent', event_id=session["event_id"]))
        
    else: 
        events = session["events"]
        
        # deal with that has no results
        if not events:
            flash('No Events Match Your Search :(')
            return redirect(url_for("search"))
            noevents = True;
        else:
            return render_template("searchresults.html", events = events)
        
@app.route("/editevent", methods=["GET", "POST"])
@login_required
@event_required
def editevent():
    if request.method == 'POST':
        
        # checks
        fields = [["name", "Name"], ["startdate", "Start Date"],
                ["enddate", "End Date"], ["starttime", "Start Time"],
                ["endtime", "End Time"]]
        
        if not required_info(fields):
            event = db.execute("SELECT * FROM events WHERE id=:id", id=session["event_id"])
            event = event[0]
            return render_template("editevent.html", event = event)
        
        if request.form.get("type") == "--Select an Event Type--":
            event = db.execute("SELECT * FROM events WHERE id=:id", id=session["event_id"])
            event = event[0]
            flash('Must Select An Event Type')
            return render_template("editevent.html", event = event)
        
        # check dates
        if not check_dates(request.form.get("startdate"), request.form.get("enddate"), request.form.get("starttime"), request.form.get("endtime")):
            event = db.execute("SELECT * FROM events WHERE id=:id", id=session["event_id"])
            event = event[0]
            return render_template("editevent.html", event = event)
        
        """Register!"""
        
        # upload image
        filename = "NULL"
        
        if 'file' in request.files:
            file = request.files['file']
            
            # if user does not select file, browser also submit a empty part without filename
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    
        photo = filename
        
        # update SQL if new image uploaded, delete old image
        if filename != "NULL":
            # delete old image, if there is one
            oldphoto = db.execute("SELECT photo FROM events WHERE id = :id", id = session["event_id"])
            oldphoto = oldphoto[0]["photo"]
            if oldphoto != "NULL":
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], oldphoto))
            
            db.execute("""UPDATE events SET name = :name, type = :type, 
            startdate = :startdate, enddate = :enddate, description = :description,
            link = :link, photo = :photo, eventid = :eventid, orgid = :orgid,
            location = :location, starttime = :starttime, endtime = :endtime
                WHERE id = :id""",
                name = request.form.get("name"),
                type = request.form.get("type"),
                startdate = request.form.get("startdate"),
                enddate = request.form.get("enddate"),
                description = request.form.get("description"),
                link = request.form.get("link"),
                photo = photo,
                eventid = "hello",
                orgid = session["org_id"],
                location = request.form.get("location"),
                starttime = request.form.get("starttime"),
                endtime = request.form.get("endtime"),
                id = session["event_id"])
        
        # else keep old image, do not update that link
        else:
            db.execute("""UPDATE events SET name = :name, type = :type, 
            startdate = :startdate, enddate = :enddate, description = :description,
            link = :link, eventid = :eventid, orgid = :orgid,
            location = :location, starttime = :starttime, endtime = :endtime
                WHERE id = :id""",
                name = request.form.get("name"),
                type = request.form.get("type"),
                startdate = request.form.get("startdate"),
                enddate = request.form.get("enddate"),
                description = request.form.get("description"),
                link = request.form.get("link"),
                eventid = "hello",
                orgid = session["org_id"],
                location = request.form.get("location"),
                starttime = request.form.get("starttime"),
                endtime = request.form.get("endtime"),
                id = session["event_id"])
        
        
        # redirect user to home page
        return redirect(url_for('viewevent', event_id=session["event_id"]))
        
    else:
        event = db.execute("SELECT * FROM events WHERE id=:id", id = session["event_id"])
        event = event[0]
        return render_template("editevent.html", event = event)
        
@app.route("/googlecal")
@event_required
def googlecal():
    # from google api links specified at beginning of app
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))
    else:
        event = db.execute("""SELECT *
                            FROM events
                            WHERE id = :id""", id=session["event_id"])
        event = event[0]
        name = event["name"]
        
        # https://developers.google.com/google-apps/calendar/create-events
        # google api for adding an event
        event = {
          'summary': event["name"],
          'location': event["location"],
          'description': event["description"] + "\n" + event["link"],
          'start': {
            'dateTime': event["startdate"] + "T" + event["starttime"] + ":00-05:00",
            'timeZone': 'America/New_York',
          },
          'end': {
            'dateTime': event["enddate"] + "T" + event["endtime"] + ":00-05:00",
            'timeZone': 'America/New_York',
          }
        }
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
        event = service.events().insert(calendarId='primary', body=event).execute()
        return render_template("googlecal.html", name = name)