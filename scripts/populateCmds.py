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
  cmds = [u'hn', u'woot', u'reddit', u'g', u'gh']
  urls = [unicode('http://news.ycombinator.com'), unicode('http://www.woot.com'),
  unicode('http://www.reddit.com'), unicode('http://www.google.com/search?q={s}'),
  unicode('https://github.com/{u}/{p}')]
  descrip = [u'returns headlines of hackernews', u"woot's daily deal", 
  u'front page headlines of reddit', u'results from google search', u'readme from github project']
  examples = [u'hn', u'woot', u'reddit', u'g s.apples', u'gh u.twitter p.bootstrap']
  switches = [[], [], [], [{'switch':u's', 'default':u''}],
  [{'switch':u'u', 'default':u'twitter'}, {'switch':u'p', 'default':u'bootstrap'}]]

  includes = [[{'tag':u'td','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'h2', 'matches':[{'type':u'class', 'value':u'fn'}]},
  {'tag':u'h3', 'matches':[{'type':u'class', 'value':u'price'}]}],
  [{'tag':u'a','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'span', 'matches':[{'type':u'class', 'value':u'st'}]}],
  [{'tag':u'article', 'matches':[{'type':u'class', 'value':u'markdown-body'}]},
  {'tag':u'article', 'matches':[{'type':u'class', 'value':u'entry-content'}]}],
  ]

  excludes = [[{'tag':u'td','matches':[{'type':u'align', 'value':u'right'}]}], [],
  [], [], []]

  enumerates = [False, False, True, False, False]
  # find the owner
  owner = db.Users.find_one({'number':'+19193971139'})
  for i in xrange(len(cmds)):
    custom = db.Commands()
    custom.cmd = cmds[i]
    custom.description = descrip[i]
    custom.switches = switches[i] 
    custom.includes = includes[i]
    custom.excludes = excludes[i]
    custom.owner = owner._id
    custom.url = urls[i]
    custom.enumerate = enumerates[i]
    custom.example = examples[i]
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
    
  
