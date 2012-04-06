import datetime
from logger import log
from globalConfigs import *

@connection.register
class Numbers(Document):
  __collection__ = 'numbers'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode,
    'email' : unicode,
    'active' : datetime.datetime,
    'requests' : [{	
      'time': datetime.datetime,
      'message': unicode, 
    }],
  }
  # ensuring unique numbers
  indexes = [{ 
    'fields':['number'], 
    'unique':True, 
  }]
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
  use_dot_notation = True 

@connection.register
class ReqCmds(Document):
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
  use_dot_notation = True 
