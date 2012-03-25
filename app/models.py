import datetime
import pymongo
from mongokit import Connection, Document

DATABASE_GET = 'get'
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017
DEBUG = True
SECRET_KEY = 'getOuttaHereKey'

connection = Connection(MONGODB_HOST, MONGODB_PORT)
db = connection.get


@connection.register
class Numbers(Document):
  __collection__ = 'numbers'
  __database__ = DATABASE_GET
  structure = {
    'number' : int,
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
  __database__ = DATABASE_GET
  structure = {
    'number' : int,
    'minute' : int,
    'command' : unicode,
    'time' : datetime.datetime
  }
  use_dot_notation = True 

@connection.register
class ReqCmd(Document):
  __collection__ = 'reqcmd'
  __database__ = DATABASE_GET
  structure = {
    'number' : int,
    'request' : unicode,
    'time' : datetime.datetime
  }
  use_dot_notation = True 
