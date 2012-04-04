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
from logger import log

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

@app.route('/hangup', methods=["POST"])
def hangup():
  return json_res({'success': 'hit hangup'})

@app.route('/requests', methods=["POST"])
def requests():
  print "REACHED: /request\n"
  # this request should only be accessed through twilio
  fromNumber = request.form.get('From', None)
  msg = request.form.get('Body', None).lower()
  log('access', 'REQUEST: '+fromNumber+' '+msg)
  
  currDate = datetime.datetime.utcnow()
  number = db.numbers.find_one({'number': fromNumber})
  req = {'time':currDate, 'message':msg}
  
  com = Commander()
  if not number or number['active'] >= currDate or len(number['requests']) <= 3:
    # add it to cmd queue and add it to numbers collection
    if not number:
      number = db.Numbers()
      number.number = fromNumber
      number.active = currDate
      number.requests = [req]
      number.save()
    else:
      db.numbers.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: db updated")
    com.parseCommand(msg, fromNumber)	
  else:
    # they need to pay
    db.numbers.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: Need to pay "+fromNumber)
    com.sendMsg("You have used up your Gladomus calls/texts. Please subscribe at www.gladomus.com", fromNumber)
  
  return json_res({'success': 'hit requests'})

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
  app.run(port=8000)
