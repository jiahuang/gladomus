import datetime
from logger import log
from globalConfigs import *
import string
from random import sample, choice
import bcrypt

def generatePw():
  # generate new pw
  chars = string.letters + string.digits
  length = 8
  pw = ''.join(choice(chars) for _ in range(length))
  return pw

@connection.register
class Users(Document):
  __collection__ = 'users'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode,
    'email' : unicode,
    'freeMsg' : int,
    'paidMsg' : int,
    'requests' : [{	
      'time': datetime.datetime,
      'message': unicode,
    }],
    'cmds': [pymongo.objectid.ObjectId], #custom commands they've added
    'pw' : unicode,
  }
  # ensuring unique numbers
  indexes = [{ 
    'fields':['number'], 
    'unique':True, 
  }]
  default_values = {
    'email':u'',
    'cmds':[],
    'freeMsg':10,
    'paidMsg':0,
    'pw':bcrypt.hashpw(generatePw(), bcrypt.gensalt()).decode()
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

# keywords should be created for switches, cmd, description, example
def populateKeywords(listOfItems):
  keywords = []
  for item in listOfItems:
    if "description" in item:
      keywords = keywords + unicode(item['description']).lower().split(' ')
    else:
      keywords = keywords + unicode(item).lower().split(' ')
  #print keywords
  return list(set(keywords))
  
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
    'isGlobal':bool,
    'enumerate': bool, # if true enumerates results
    'switches' : [{
      'description':unicode,
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
    'excludes' : [{
      'tag':unicode, #div, span, p, etc
      'matches': [{
        'type':unicode, #class, id, href, etc
        'value':unicode, # value of class/id
        }]
      }],
    'owner' : pymongo.objectid.ObjectId,
    'dateUpdated': datetime.datetime,
    '_keywords':[unicode],
  }
  indexes = [{ 
    'fields':['cmd', '_keywords'],
  }]
  default_values = {
    'switches': [],
    'includes':[],
    'excludes':[],
    'isGlobal': False,
    'enumerate': False,
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
