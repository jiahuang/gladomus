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
from urlparse import urlparse

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
  salt = bcrypt.gensalt()
  hash = bcrypt.hashpw(pw, salt).decode()
  print "autopw", pw, salt, hash
  db.users.update({'number':number}, {'$set':{'pw':hash, 'salt':salt}})
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

# cleaning switches, includes, and excludes
def cleanArray(arr, keys):
  # make sure keys include valid values for each element in arr
  newArr = []
  for item in arr:
    isEmpty = False
    for key in keys:
      if unicode(key) not in item:
        return json_res({'error': 'Error: '+item+" is missing a value for "+key})
      if item[key] == "":
        isEmpty = True
        break
    if not isEmpty:
      newArr.append(item)
  return newArr

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
      print "sort"
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
  
  if not user:
    # new user, auto generate pw and text them
    user = db.Users()
    user.number = fromNumber
    user.requests = [req]
    user.save()
    pw = autoPw(fromNumber)
    if msg.lower() == 'signup' or msg.lower() == "newpw":
      com = Commander(fromNumber, 'gladomus') #reinitiate because we just created the user
      com.processMsg("Welcome to Textatron. You can log in with this number and this auto generated password: "+pw+" Text 'help' for a list of commands", False, False)      
  elif msg.lower() == 'signup':
    # they already called another command before signup
    pw = autoPw(fromNumber)
    com.processMsg("Welcome to Textatron. You can log in with this number and this auto generated password: "+pw+" Text 'help' for a list of commands", False, False)
  elif msg.lower() == 'newpw':
    pw = autoPw(fromNumber)
    com.processMsg("Your password has been reset to: "+pw, False, False)
  elif user['freeMsg'] < 0 and user['paidMsg'] < 0:
    # they need to pay
    db.users.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: Need to pay "+fromNumber)
    com.processMsg("You have used up your texts. Add more at www.textatron.com", False, False)
  else:
    db.users.update({'number':fromNumber}, {'$push':{'requests':req}})
    log('access', "REACHED: new request "+msg+" from "+fromNumber)
    Commander(fromNumber, msg).start()
  
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

@app.route('/createCommands/test/<cmdId>', methods=['POST'])
def testCommand(cmdId="new"):
  # sets up fake command
  # if cmdId is passed in, we are editing
  isEdit = False
  try:
    inputCmd = json.loads(request.form.get('cmd', ''))
    testCmd = request.form.get('test', '')
    user = getUser()
    if user:
      # check if its an edit
      editingCmd = None
      if cmdId != 'new' and pymongo.objectid.ObjectId(cmdId) in user.cmds:
        editingCmd = db.Commands.find_one({"_id":pymongo.objectid.ObjectId(cmdId)})
        if editingCmd:
          isEdit = True
          
      if not editingCmd:
      # not editing, new creation
        userCmds = list(db.Commands.find({'_id':{'$in':user.cmds}}, {'cmd':1, 'tested':1}))
        #rint userCmds
        for userCmd in userCmds:
          if userCmd['cmd'] == inputCmd['cmd'].lower():
            if not userCmd['tested']:
              # delete the old tested command
              db.Commands.remove({'_id':userCmd['cmd']['_id']})
            else:
              return json_res({'error': 'Error: You already have a command with the same name. Please change the name'})
        editingCmd = db.Commands()
    
    else:
      user = getDefaultUser()

    # checking url to make sure its legit
    urlparts = urlparse(inputCmd['url'])
    if not urlparts.scheme:
      inputCmd['url'] = 'http://'+inputCmd['url']
    editingCmd.cmd = inputCmd['cmd'].lower()
    editingCmd.url =  inputCmd['url']
    editingCmd.description = inputCmd['description']
    editingCmd.example = inputCmd['example']
    editingCmd.enumerate = inputCmd['enumerate']

    editingCmd.switches = cleanArray(inputCmd['switches'], ['switch', 'description'])
    editingCmd.includes = cleanArray(inputCmd['includes'], ['tag', 'matches'])
    editingCmd.excludes = cleanArray(inputCmd['excludes'], ['tag', 'matches'])
    editingCmd.owner = user._id
    editingCmd.save()
    if not isEdit:
      user.cmds.append(editingCmd._id)
      user.save()
    
    session['cmd'] = editingCmd._id #keep track of which command we saved
    #print postCmd._id
    com = Commander(user.number, 'gladomus')
    print 'test', testCmd
    res = com.customCommandHelper(editingCmd._id, testCmd)
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

@app.route('/createCommands/edit/<cmdId>', methods=['GET'])
def editCommand(cmdId):
  # load up cmd with that id
  cmd = db.Commands.find_one({'_id':pymongo.objectid.ObjectId(cmdId)})
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
      inputCmd['switches'] = cleanArray(inputCmd['switches'], ['switch', 'description'])
      inputCmd['includes'] = cleanArray(inputCmd['includes'], ['tag', 'matches'])
      inputCmd['excludes'] = cleanArray(inputCmd['excludes'], ['tag', 'matches'])
      # make sure user doesn't already have this command
      user = getUser()
      # check that the user has a tested cmd
      if "cmd" not in session:
        return json_res({'error': 'Error: you must test your command first.'})
      cmd = db.Commands.find_one({'_id':session['cmd']})
      if not cmd or len(inputCmd) < 8:
        return json_res({'error': 'Error: you must test your command first.'})
      # check to make sure that the tested command is the same as the one they are submitting
      for key in inputCmd:
        if cmd[key] != inputCmd[key]:
          print key, cmd[key], inputCmd[key]
          return json_res({'error': 'Error: you must test your command first.'})
      cmd.tested = True
      cmd.dateUpdated = datetime.datetime.utcnow()
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
      return json_res({'error':'Either the number or the password is not in our system. Did you put in the right country code?'})

    hash = None
    try:
      hash = bcrypt.hashpw(request.form.get('password'), user.salt)
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
