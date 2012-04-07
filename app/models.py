import datetime
from logger import log
from globalConfigs import *

@connection.register
class Users(Document):
  __collection__ = 'users'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode,
    'email' : unicode,
    'active' : datetime.datetime,
    'requests' : [{	
      'time': datetime.datetime,
      'message': unicode, 
    }],
    'cmds': [pymongo.objectid.ObjectId], #custom commands they've added
    'owns': [pymongo.objectid.ObjectId], #custom commands they own & can edit
  }
  # ensuring unique numbers
  indexes = [{ 
    'fields':['number'], 
    'unique':True, 
  }]
  default_values = {
    'email':'',
    'cmds':[],
    'owns':[],
  }
  use_dot_notation = True 
  required_fields = ['number']

@connection.register
class Actions(Document):
  __collection__ = 'actions'
  __database__ = DATABASE_GLAD
  structure = {
    'original' : unicode, # original command
    'number' : unicode,
    'msg' : unicode,
    'command' : unicode, # parsed command
    'time' : datetime.datetime # time to execute
  }
  use_dot_notation = True 

@connection.register
class Cache(Document):
  __collection__ = 'cache'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode, 
    'data' : unicode,
    'index' : int, # index of data that user has been sent
    'time' : datetime.datetime # time cached
  }
  default_values = {
    'time':datetime.datetime.utcnow()
  }
  use_dot_notation = True 

@connection.register
class GlobalCommands(Document): #global commands
  __collection__ = 'globalCommands'
  __database__ = DATABASE_GLAD
  structure = {
    'cmd' : unicode, 
    'dateUpdated': datetime.datetime,
  }
  default_values = {
    'dateUpdated':datetime.datetime.utcnow()
  }
  use_dot_notation = True 

@connection.register
class Commands(Document): #user generated commands
  use_schemaless = True
  __collection__ = 'commands'
  __database__ = DATABASE_GLAD
  structure = {
    'cmd' : unicode, 
    'url': unicode,
    'description':unicode,
    'example':unicode,
    'switches' : [{
      'switch':unicode,
      'default':unicode,
      }],
    'includes' : [{
      'tag':unicode, #div, span, p, etc
      'matches': [{
        'type':unicode, #class, id, href, etc
        'value':unicode, # value of class/id
        }]
      }],
    # not doing excludes for now
    #'exclude' : [{
    #  'tag':unicode, #div, span, p, etc
    #  'matches': {[
    #    'type':unicode, #class, id, href, etc
    #    'value':unicode, # value of class/id
    #    ]}
    #  }],
    'owner' : pymongo.objectid.ObjectId,
    'dateUpdated': datetime.datetime,
  }
  indexes = [{ 
    'fields':['cmd'], 
  }]
  default_values = {
    'switches': [{
      'switch': '',
      'default': '',
    }],
    'includes':[],
    'dateUpdated':datetime.datetime.utcnow()
  }
  use_dot_notation = True 

@connection.register
class ReqCmds(Document): # user requests
  __collection__ = 'reqCmds'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode,
    'request' : unicode,
    'time' : datetime.datetime,
    'msg' : unicode
  }
  indexes = [{ 
    'fields':['number'], 
  }]
  default_values = {
    'time':datetime.datetime.utcnow()
  }
  use_dot_notation = True 
