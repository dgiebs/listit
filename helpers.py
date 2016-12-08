import csv
import urllib.request

from datetime import datetime, date

from flask import redirect, render_template, request, session, url_for, flash
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# wrapper for sites that require an event to be selected
def event_required(f):
    """
    Decorate routes to require a event to be selected

    based off of above login_required function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("event_id") is None:
            return redirect(url_for("index", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# limit allowed extensions
# http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','TXT', 'PDF', 'PNG', 'JPG', 'JPEG', 'GIF'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
  
# checks all "required field" errors         
def required_info(fields):
    for item in fields:
        if not request.form.get(item[0]):
            message = "Must Provide " + item[1]
            flash(message)
            return False
    return True

# make datetime more readable, and shorten description
def convert_datetime(events):
    for item in events:
        
        # convert dates and times to more readable format
        dateinput = "%Y-%m-%d"
        timeinput = "%H:%M"
        dateoutput = "%a %b %d"
        timeoutput = "%I:%M %p"
        # convert from string to datetime, then from date time to 'readable' string
        item["startdate"] = datetime.strptime(item["startdate"], dateinput)
        item["startdate"] = date.strftime(item["startdate"], dateoutput)
        
        item["enddate"] = datetime.strptime(item["enddate"], dateinput)
        item["enddate"] = date.strftime(item["enddate"], dateoutput)
        
        item["starttime"] = datetime.strptime(item["starttime"], timeinput)
        item["starttime"] = datetime.strftime(item["starttime"], timeoutput)
        
        item["endtime"] = datetime.strptime(item["endtime"], timeinput)
        item["endtime"] = datetime.strftime(item["endtime"], timeoutput)
        
    return events

def shorten_description(events):
    # return only first 200 characters for the viewevents page
    for item in events:
        # shorten description
        if len(item["description"]) > 200:
            item["description"] = item["description"][:200] + "..."
            
    return events
    
def check_dates(startdate, enddate, starttime, endtime):
        
    # do date input checks
    dateinput = "%Y-%m-%d"
    startdate = datetime.strptime(startdate, dateinput)
    enddate = datetime.strptime(enddate, dateinput)
    
    # start date today or later
    if datetime.date(startdate) < datetime.today().date():
        flash('Must Input a Valid Start Date')
        return False
    # end date can't be before start date
    if datetime.date(enddate) < datetime.date(startdate):
        flash('Must Input a Valid End Date')
        return False
    # if a 1-day event, end time must be after start time
    if datetime.date(enddate) == datetime.date(startdate) and endtime < starttime:
        flash('Must Input a Valid End Time')
        return False
        
    return True