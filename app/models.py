import datetime
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
class ReqCmds(Document):
  __collection__ = 'reqCmds'
  __database__ = DATABASE_GLAD
  structure = {
    'number' : unicode,
    'request' : unicode,
    'time' : datetime.datetime,
    'msg' : unicode
  }
  use_dot_notation = True 
