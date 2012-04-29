import sys
sys.path.append("../app/")
from models import *

def makeUser():
  user = db.Users()
  user.number = u'+19193971139'
  user.email = u'jialiya.huang0@gmail.com'
  req = {'time':datetime.datetime.utcnow(), 'msg':u'populate'}
  user.requests = [req]
  user.freeMsg = 10000
  user.salt = unicode(bcrypt.gensalt())
  user.pw = bcrypt.hashpw('123qwe', bcrypt.gensalt()).decode()
  user.save()

  user = db.Users()
  user.number = unicode(TWILIO_NUM)
  user.email = u'jialiya.huang0@gmail.com'
  req = {'time':datetime.datetime.utcnow(), 'msg':u'populate'}
  user.requests = [req]
  user.freeMsg = 10000
  user.salt = unicode(bcrypt.gensalt())
  user.pw = bcrypt.hashpw('123qwe', ).decode()
  user.save()
      
def populateGlobals():
  # populate global commands table
  cmds = ['mapw', 'mapd', 'mapp', 'wiki', 'more', 'newpw', 'signup']
  descrip = ['Gives walking directions', 'Gives driving directions', 'Gives public transit directions at a certain arrival or departure time',
  'Returns wikipedia information on particular articles',
  'If any results are more than 4 texts long, the more command sends the next part of the result',
  'Resets your password', 'Signs you up for Gladomus']
  switches = [[{'switch':u's', 'default': u'','description':u'starting location'}, {'switch':u'e', 'default':u'', 'description':u'ending location'}],
  [{'switch':u's', 'default':u'', 'description':u'starting location'}, {'switch':u'e', 'default':u'', 'description':u'ending location'}],
  [{'switch':u's', 'default':u'', 'description':u'starting location'}, {'switch':u'e', 'default':u'', 'description':u'ending location'},
  {'switch':u'a', 'default':u'', 'description':u'arrival time. (1:00PM, 13:00)'}, {'switch':u'd', 'default':u'', 'description':u'departure time. (1:00PM, 13:00)'}], 
  [{'switch':u'a', 'default':u'', 'description':u'article'},
  {'switch':u's', 'default':u'summary', 'description':u'section of the article. Can specify "toc" to get the table of contents. Can be the section number in the table of contents or the heading. '}],
  [], [], []]
  examples = ['map w s.Microsoft Building 84, WA e.Microsoft Building 26, WA',
  'map d s.Microsoft Building 84, WA e.Microsoft Building 26, WA', 'map p s.Microsoft Building 84, WA e.400 Broad St. Seattle, WA d.4:00pm',
  'wiki a.rabbits, wiki a.rabbits s.toc, wiki a.rabbits s.10.1, wiki a.rabbits s.habitat and range',
  'more', 'newpw', 'signup']
  
  owner = db.Users.find_one({'number':'+19193971139'})
  for i in xrange(len(cmds)):
    custom = db.Commands()
    custom.cmd = unicode(cmds[i])
    custom.description = unicode(descrip[i])
    custom.isGlobal = True
    custom.tested = True
    custom.owner = owner._id
    custom.switches = switches[i]
    custom.example = unicode(examples[i])
    l = list(switches[i]);
    l.append(descrip[i])
    l.append(cmds[i])
    l.append(examples[i])
    custom._keywords = populateKeywords(l)
    print custom._keywords
    custom.save()

def populateCustom():
  # populate custom commands table
  cmds = [u'hn', u'woot', u'reddit', u'g', u'gh']
  urls = [unicode('http://news.ycombinator.com'), unicode('http://www.woot.com'),
  unicode('http://www.reddit.com'), unicode('http://www.google.com/search?q={s}'),
  unicode('https://github.com/{u}/{p}')]
  descrip = [u'returns headlines of hackernews', u"woot's daily deal", 
  u'front page headlines of reddit', u'results from google search', u'readme from github project']
  examples = [u'hn', u'woot', u'reddit', u'g s.apples', u'gh u.twitter p.bootstrap']
  switches = [[], [], [], [{'switch':u's', 'default':u'', 'description':u'search query'}],
  [{'switch':u'u', 'default':u'twitter', 'description':u'github user'}, {'switch':u'p', 'default':u'bootstrap', 'description':u'project name'}]]

  includes = [[{'tag':u'td','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'h2', 'matches':[{'type':u'class', 'value':u'fn'}]},
  {'tag':u'h3', 'matches':[{'type':u'class', 'value':u'price'}]}],
  [{'tag':u'a','matches':[{'type':u'class', 'value':u'title'}]}],
  [{'tag':u'span', 'matches':[{'type':u'class', 'value':u'st'}]}],
  [{'tag':u'article', 'matches':[{'type':u'class', 'value':u'markdown-body'}]},
  {'tag':u'article', 'matches':[{'type':u'class', 'value':u'entry-content'}]}],
  ]

  excludes = [[{'tag':u'td','matches':[{'type':u'align', 'value':u'right'}]},
  {'tag':u'span','matches':[{'type':u'class', 'value':u'comhead'}]}], [],
  [], [], []]

  enumerates = [True, False, True, False, False]
  # find the owner
  owner = db.Users.find_one({'number':'+19193971139'})
  for i in xrange(len(cmds)):
    custom = db.Commands()
    custom.cmd = cmds[i]
    custom.description = descrip[i]
    custom.switches = switches[i] 
    custom.includes = includes[i]
    custom.excludes = excludes[i]
    custom.tested = True
    custom.owner = owner._id
    custom.url = urls[i]
    custom.enumerate = enumerates[i]
    custom.example = examples[i]
    l = list(switches[i]);
    l.append(descrip[i])
    l.append(cmds[i])
    l.append(examples[i])
    custom._keywords = populateKeywords(l)
    custom.save()
    owner.cmds.append(custom._id)
    owner.save()

def main(name):
  makeUser()
  populateGlobals()
  populateCustom()
  
if __name__ == '__main__':
  main(*sys.argv)
    
  
