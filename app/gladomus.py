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
from commander import Commander, clean
import twilio.twiml
from logger import log
import simplejson

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
def getDefaultUser():
  return db.Users.find_one({'number':TWILIO_NUM})
  
def getUser():
  if 'logged_in' in session and session['logged_in'] == True: 
    if 'uid' in session:
      return db.Users.find_one({'_id':session['uid']})
  return None

def json_res(obj):
  # convert datetimes to miliseconds since epoch
  dthandler = lambda obj: time.mktime(obj.timetuple())*1000 if isinstance(obj, datetime.datetime) else None
  return Response(json.dumps(obj, default=dthandler), mimetype='application/json')

def autoPw(number):
  pw = generatePw()
  # updates associated number w/ pw
  db.user.update({'number':number}, {'$set':{'pw':bcrypt.hashpw(pw, bcrypt.gensalt()).decode()}})
  return pw

def jsonCmd_res(objs, isCursor):
  if isCursor:
    objs = list(objs)
  if objs == None or len(objs) == 0:
    return Response(False, mimetype='application/json')
  # assumes that objs is a cursor
  if 'logged_in' in session and session['logged_in'] == True:
    cmds = getUser().cmds#db.Users.find_one({'_id':session['uid']}, {'cmds':1})
  else:
    cmds = []
  #print cmds
  jsonObjs = []
  for obj in objs:
    jsonObj = {}
    if obj._id in cmds:
      jsonObj['added'] = 1
    else:
      jsonObj['added'] = 0
    jsonObj['cmd'] = obj.cmd
    jsonObj['isGlobal'] = obj.isGlobal
    jsonObj['description'] = obj.description
    jsonObj['dateUpdated'] = time.mktime(obj.dateUpdated.timetuple())*1000
    jsonObj['switches'] = obj.switches
    jsonObj['example'] = obj.example
    jsonObj['id'] = str(obj._id)
    jsonObjs.append(jsonObj)

  return Response(json.dumps(jsonObjs), mimetype='application/json')

########################################################################
# Routes
########################################################################
@app.route('/commandsAjax', methods=["POST"])
def commandsAjax():
  page = int(request.form.get("page"))
  sortQuery = int(request.form.get('sortBy'))
  sortByList = ['added','cmd', 'dateUpdated']
  order = int(request.form.get('order'))
  if order == 1:
    order = pymongo.ASCENDING
  else:
    order = pymongo.DESCENDING

  isCursor = True
  # if its a search query
  search = unicode(clean(request.form.get("search").lower()))
  user = getUser()
  cmdList = None
  if search != '':
    if sortQuery >= 0:
      if sortByList[sortQuery] == 'added' and user:
        # sort by commands user has added
        userCmds = user.cmds
        cmdList = list(db.Commands.find({'tested':True, '_keywords':search, '_id':{'$in':userCmds}}))
        altList = list(db.Commands.find({'tested':True, '_keywords':search, '_id':{'$nin':userCmds}}))
        if order == pymongo.DESCENDING: cmdList = cmdList + altList
        else: cmdList = altList + cmdList
        cmdList = cmdList + list(db.Commands.find({'tested':True, '_keywords':search, '_id':{'$nin':userCmds}}))
        isCursor = False
        cmdList = cmdList[(page-1)*20:page*20]
      elif sortByList[sortQuery] != 'added':
        cmdList = db.Commands.find({'tested':True, '_keywords':search}).sort(sortByList[sortQuery], order).skip((page-1)*20).limit(20)
    else:
      cmdList = db.Commands.find({'tested':True, '_keywords':search}).skip((page-1)*20).limit(20)
  else:
    if sortQuery >= 0:
      if sortByList[sortQuery] == 'added' and user:
        # sort by commands user has added
        userCmds = user.cmds
        cmdList = list(db.Commands.find({'tested':True, '_id':{'$in':userCmds}}))
        altList = list(db.Commands.find({'tested':True, '_id':{'$nin':userCmds}}))
        if order == pymongo.DESCENDING: cmdList = cmdList + altList
        else: cmdList = altList + cmdList
        cmdList = cmdList[(page-1)*20:page*20]
        isCursor = False
      elif sortByList[sortQuery] != 'added':
        cmdList = db.Commands.find({'tested':True}).sort(sortByList[sortQuery], order).skip((page-1)*20).limit(20)
   
  if cmdList == None:
    globalCmds = list(db.Commands.find({'tested':True,'isGlobal':True}))
    # find by most recently updated
    cmdList = globalCmds + list(db.Commands.find({'tested':True, 'isGlobal':False}).sort('dateUpdated', order).limit(20))
    cmdList = cmdList[(page-1)*20:page*20]
    isCursor = False
  return jsonCmd_res(cmdList, isCursor)
    
@app.route('/error')
def error(error_msg):
  return render_template("error.html", error = error_msg)

@app.route('/requests', methods=["POST"])
def requests():
  print "REACHED: /request\n"
  # this request should only be accessed through twilio
  fromNumber = request.form.get('From', None)
  msg = clean(request.form.get('Body', None).lower())
  log('access', 'REQUEST: '+fromNumber+' '+msg)
  
  currDate = datetime.datetime.utcnow()
  user = db.users.find_one({'number': fromNumber})
  req = {'time':currDate, 'message':msg}

  com = Commander(fromNumber, 'gladomus')
  # if command is reset password
  if msg == 'newpw':
    if user:
      pw = autoPw(fromNumber)
      com.processMsg("Your password has been reset to: "+pw, False, False)
    else:
      com.processMsg("You do not have a Gladomus account. Text 'signup' to signup for Gladomus.", False, False)
    return json_res({'success': 'new pw hit'})

  if not user or user['active'] >= currDate or len(user['requests']) <= 10:
    # add it to cmd queue and add it to numbers collection
    if not user:
      # new user, auto generate pw and text them
      user = db.Users()
      user.number = fromNumber
      user.active = currDate
      user.requests = [req]
      user.save()
      pw = autoPw(fromNumber)
      #com.processMsg("Welcome to Gladomus. You can log in with this number and this auto generated password: "+pw+" Text 'help' for a list of commands", False, False)
    else:
      db.users.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: new request "+msg+" from "+fromNumber)
    Commander(fromNumber, msg).start()
  else:
    # they need to pay
    db.users.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: Need to pay "+fromNumber)
    com.processMsg("You have used up your texts. Please subscribe at www.textatron.com", False, False)
  
  return json_res({'success': 'hit requests'})

@app.route('/pay', methods=['POST'])
def pay():
  # send payments off to amazon
  return json_res({'success':"Your order has been successfully processed."})

@app.route('/updateUser', methods=['POST'])
def updateUser():
  # allows users to update their pw, email, and number

  return json_res({'success': 'Your account was updated successfully'})
  
@app.route('/logout', methods=['GET'])
def logout():
  session.pop('logged_in', None)
  session.pop('uid', "")
  session.pop('number', "")
  if "cmd" in session:
    session.pop('cmd', "")
  #flash('You were logged out')
  return redirect(url_for('main'))

@app.route('/createCommands/test', methods=['POST'])
def testCommand():
  # sets up fake command
  try:
    inputCmd = json.loads(request.form.get('cmd', ''))
    #print inputCmd
    # make sure user doesn't already have this command
    user = getUser()
    if user:
      #return json_res({'error': 'Error: You must be logged in to create a command'})
      userCmds = list(db.Commands.find({'_id':{'$in':user.cmds}}, {'cmd':1}))
      for userCmd in userCmds:
        if userCmd['cmd'] == inputCmd['cmd'].lower():
          if not userCmd['cmd']['tested']:
            # delete the old tested command
            db.Commands.remove({'_id':userCmd['cmd']['_id']})
          else:
            return json_res({'error': 'Error: You already have a command with the same name. Please change the name'})
    else:
      user = getDefaultUser()
        
    postCmd = db.Commands()
    postCmd.cmd = inputCmd['cmd'].lower()
    postCmd.url = inputCmd['url'] # TODO: make sure this url is clean
    postCmd.description = inputCmd['description']
    postCmd.example = inputCmd['example']
    postCmd.enumerate = inputCmd['enumerate']
    postCmd.switches = inputCmd['switches']
    postCmd.includes = inputCmd['includes']
    postCmd.excludes = inputCmd['excludes']
    postCmd.owner = user._id
    postCmd.save()
    user.cmds.append(postCmd._id)
    user.save()
    
    session['cmd'] = postCmd._id #keep track of which command we saved
    #print postCmd._id
    com = Commander(user.number, 'gladomus')
    res = com.customCommandHelper(postCmd._id, postCmd.example)
  except:
    return json_res({'error': 'Error: the command could not be tested. Make sure all the fields are properly formatted. Extended output:'+str(sys.exc_info())})
  # returns results
  return json_res(res)

@app.route('/createCommands/add/<cmdId>', methods=['POST'])
def addCommand(cmdId):
  user = getUser()
  cmdId = pymongo.objectid.ObjectId(cmdId)
  if user:
    if cmdId in user.cmds:
      # remove from commands
      user.cmds.remove(cmdId)
      user.save()
      return json_res({'success':'Successfully removed this command from your list'})
    else:
      user.cmds.append(cmdId)
      user.save()
      return json_res({'success':'Successfully added this command'})
  else:
    flash('Error: you must be logged in to add commands')
  return json_res({'error':'you must be logged in to add a command'})

@app.route('/createCommands/edit/<cmdId>', methods=['GET', 'POST'])
def editCommand(cmdId):
  # load up cmd with that id
  cmd = db.Commands.find_one({'_id':pymongo.objectid.ObjectId(cmdId)})
  if request.method == 'POST':
    # is an edit
    postCmd = request.form.get('cmd')
    # populate keywords
    postCmd._keywords = populateKeywords([postCmd.switches, postCmd.descrip, postCmd.cmds, postCmd.examples])
    # if user already owns this command, update it
    user = getUser()
    if user:
      if cmdId in user.cmds:
        # just edit the command and save it
        db.Commands.update({'_id':cmdId}, {'$set':{postCmd}})
      else:
        # create new command and add it under user
        newCmd = db.Commands
        newCmd.setFields(postCmd)
        newCmd.save()
        user.cmds.append(newCmd._id)
        user.save()
    # if no user, add it with gladomus as the owner
    else:
      newCmd = db.Commands
      newCmd.setFields(postCmd)
      newCmd.save()
      GLADOMUS_USER.cmds.append(newCmd._id)
      GLADOMUS_USER.save()
    #flash('Successfully added your command')
    return redirect(url_for('commands'))
  # GET
  if not cmd:
    # flash error
    #flash('Error: We could not find that command')
    return render_template('createCommands.html') 
  # command was found
  return render_template('createCommands.html', cmd=cmd)
  

@app.route('/createCommands/new', methods=['GET', 'POST'])
def createCommands():
  if request.method == "POST":
    try:
      inputCmd = json.loads(request.form.get('cmd', ''))
      print inputCmd
      # make sure user doesn't already have this command
      user = getUser()
      #userCmds = list(db.Commands.find({'_id':{'$in':user.cmds}}, {'cmd':1}))
      #for userCmd in userCmds:
      #  if userCmd['cmd'] == inputCmd['cmd'].lower():
      #    return json_res({'error': 'Error: You already have a command with the same name. Please change the name'})
      '''postCmd = db.Commands()
      postCmd.cmd = inputCmd['cmd'].lower()
      postCmd.url = inputCmd['url'] # TODO: make sure this url is clean
      postCmd.description = inputCmd['description']
      postCmd.example = inputCmd['example']
      postCmd.enumerate = inputCmd['enumerate']
      postCmd.switches = inputCmd['switches']
      postCmd.includes = inputCmd['includes']
      postCmd.excludes = inputCmd['excludes']
      postCmd.owner = user._id
      postCmd.save()'''    
      # check that the user has a tested cmd
      if "cmd" not in session:
        return json_res({'error': 'Error: you must test your command first.'})
      cmd = db.Commands.find_one({'_id':session['cmd']})
      if not cmd or len(inputCmd) < 8:
        return json_res({'error': 'Error: you must test your command first.'})
      # check to make sure that the tested command is the same as the one they are submitting
      for key in inputCmd:
        if cmd[key] != inputCmd[key]:
          return json_res({'error': 'Error: you must test your command first.'})
      cmd.tested = True
      cmd.save()
      session.pop('cmd','') 
    except:
      return json_res({'error': 'Error: the command could not be created. '+str(sys.exc_info()[0])})
    
    # new command is created
    return json_res({'success':'The command has been successfully created'})

  # its a get
  return render_template('createCommands.html')
  
@app.route('/login', methods=['GET','POST'])
def login():
  if request.method == 'POST':
    number = request.form.get('number')
    # make sure neither value is blank
    if not number or not request.form.get('password'):
      return json_res({'error':'Please fill in both your number and password.'})

    replace = ['-', '.', '(', ')']
    for r in replace: number = number.replace(r, '')
    
    if len(number) == 10:
      # pad with +1
      number = '+1'+number
    elif len(number) > 10 and number[0] != '+':
      number = '+'+number
      
    user = db.Users.find_one({'number': number})
    
    if not user:
      return json_res({'error':'Either the number or the password is not in our system.'})

    hash = None
    try:
      hash = bcrypt.hashpw(request.form.get('password'), user.pw)
    except:
      pass
    if hash != user.pw:
      print hash
      print user.number, user.pw
      return json_res({'error':'Either the username or the password is not in our system'})
      
    session['logged_in'] = True
    session['uid'] = user._id
    session['number'] = user.number
    session['free'] = user.freeMsg
    session['paid'] = user.paidMsg
    return json_res({'success':"Welcome to Gladomus"}) #render_template('commands.html')

  # GET
  return render_template('loginPopup.html')
  
########################################################################
# Static routes
########################################################################

@app.route('/', methods=['GET'])
def main():
  if "logged_in" in session and session['logged_in']:
    return render_template('settings.html')
  else:
    return render_template('main.html')

@app.route('/commands', methods=['GET'])
def commands():
  return render_template('commands.html')

########################################################################
# Entry
########################################################################

if __name__ == '__main__':
  app.run(port=8000)
