import sys
sys.path.append("../app/")
from models import *

def makeUser():
  user = db.Users()
  user.number = u'+19193971139'
  user.email = u'jialiya.huang0@gmail.com'
  user.active = datetime.datetime.utcnow() + datetime.timedelta(days=5)
  req = {'time':datetime.datetime.utcnow(), 'msg':u'populate'}
  user.requests = [req]
  user.save()
  
def populateGlobals():
  # populate global commands table
  cmds = ['map', 'wiki', 'more', 's', 'help', 'call']
  for cmd in cmds:
    glb = db.GlobalCommands()
    glb.cmd = unicode(cmd)
    glb.save()

def populateCustom():
  # populate custom commands table
  cmds = [u'hn', u'woot', u'reddit', u'g']
  urls = [unicode('http://news.ycombinator.com'), unicode('http://www.woot.com'),
  unicode('http://www.reddit.com'), unicode('http://www.google.com/search?q=s.')]
  descrip = [u'returns headlines of hackernews', u"woot's daily deal", 
  u'front page headlines of reddit', u'results from google search']
  switches = ['', '', '', u's']
  includes = [[{'tag':u'td','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'h2', 'matches':[{'type':u'class', 'value':u'fn'}]},
  {'tag':u'h3', 'matches':[{'type':u'class', 'value':u'price'}]}],
  [{'tag':u'a','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'span', 'matches':[{'type':u'class', 'value':u'st'}]}]]

  # find the owner
  owner = db.Users.find_one({'number':'+19193971139'})
  for i in xrange(len(cmds)):
    custom = db.Commands()
    custom.cmd = cmds[i]
    custom.description = descrip[i]
    if switches[i] = '':
      custom.switches = []
    else:
      custom.switches = [{'switch':switches[i], 'default':''}] # default values don't work in nested items
    custom.includes = includes[i]
    custom.owner = owner._id
    custom.url = urls[i]
    custom.save()
    owner.cmds.append(custom._id)
    owner.owns.append(custom._id)
    owner.save()

def main(name):
  populateGlobals()
  makeUser()
  populateCustom()
  
if __name__ == '__main__':
  main(*sys.argv)
    
  
