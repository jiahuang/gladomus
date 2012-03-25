#
# GetOuttaHere 
# 2012
# Jialiya Huang
#

########################################################################
# Imports
########################################################################

import flask
import shutil
from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash, Response
from contextlib import closing
import os
import datetime, sys, json, time, uuid, subprocess
from models import *
import twilio.twiml

########################################################################
# Configuration
########################################################################

DEBUG = True
# create app
app = Flask(__name__)
app.config.from_object(__name__)

########################################################################
# Helper functions
########################################################################
	
def json_res(obj):
	# convert datetimes to miliseconds since epoch
	dthandler = lambda obj: time.mktime(obj.timetuple())*1000 if isinstance(obj, datetime.datetime) else None
	return Response(json.dumps(obj, default=dthandler), mimetype='application/json')

########################################################################
# Routes
########################################################################

@app.route('/error')
def error(error_msg):
  return render_template("error.html", error = error_msg)

@app.route('/request')
def request():
  fromNumber = request.args.get('From', None)
  msg = request.args.get('Body', None).lower()
  # TODO: parse out the body message
  cmd = msg.split(' ')[0]
  minutes = int(msg.split(' ')[1])
	
  currDate = datetime.datetime.utcnow()
  # check db
  number = db.numbers.find({'number': fromNumber, 'active':{'$gte':currDate}})
  req = {'time':currDate, 'message':msg}
  
  if not number:
    # add it to call queue and add it to numbers collection
    number = db.Numbers()
    number.number = fromNumber
    number.active = currDate
    number.requests = [req]
    number.save()
    
    action = db.Actions()
    action.number = number
    action.minute = minutes
    action.command = cmd
    action.time = currDate + datetime.timedelta(minuets=action.minute)
    action.save()
  elif len(number.requests) > 3:
    # they need to pay
    db.numbers.update({'number':fromNumber}, {'$push':{'requests':req}})
    resp = twilio.twiml.Response()
    resp.sms("You have used up your GetOuttaHere calls/texts. Please subscribe at www.getouttahere.me")
  return str(resp)

@app.route('/pay', methods=['POST'])
def oliners():
  # send payments off to amazon
  return json_res({'success':"Your order has been successfully processed."})
		
@app.route('/', methods=['GET'])
def main():
  return render_template('main.html')

########################################################################
# Entry
########################################################################

if __name__ == '__main__':
  app.run()
