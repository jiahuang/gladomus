#
# Gladomus 
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
from commander import Commander
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

def sendError(self, number, error):
  message = self.client.sms.messages.create(to="+1"+number, from_="+1"+self.number, body=msg)
  # TODO: log it
		
########################################################################
# Routes
########################################################################

@app.route('/error')
def error(error_msg):
  return render_template("error.html", error = error_msg)

@app.route('/hangup')
def hangup():
  return

@app.route('/request')
def request():
  # this request should only be accessed through twilio
  fromNumber = request.args.get('From', None)
  msg = request.args.get('Body', None).lower()
  currDate = datetime.datetime.utcnow()
  # check db
  number = db.numbers.find({'number': fromNumber, 'active':{'$gte':currDate}})
  req = {'time':currDate, 'message':msg}
  
  com = Commander()
  
  if not number or len(number.requests) <=3:
    # add it to cmd queue and add it to numbers collection
    if not number:
      number = db.Numbers()
      number.number = fromNumber
      number.active = currDate
      number.requests = [req]
      number.save()
    else:
      db.numbers.update({'number':fromNumber}, {'$push':{'requests':req}})
    
    com.parseCommand(msg, fromNumber)	
  else:
    # they need to pay
    db.numbers.update({'number':fromNumber}, {'$push':{'requests':req}})
    com.sendError(fromNumber, "You have used up your GetOuttaHere calls/texts. Please subscribe at www.gladomus.com")
  
  return

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
