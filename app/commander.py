from models import *
from twilio.rest import TwilioRestClient
from time import gmtime, strftime
import urllib2
import simplejson
from bingMapParser import BingMapParser
import re
from logger import log
from bs4 import BeautifulSoup
import time
from threading import Thread
from operator import itemgetter

CLIENT = TwilioRestClient(TWILIO_SID, TWILIO_AUTH)
MAX_TEXTS = 4 # max number before delaying into more

def isIntOrFloat(s):
  try:
    int(s)
  except ValueError:
    try:
      float(s)
    except ValueError:
      return False
  return True

def clean(s):
  s = re.sub("\s+", " ", s)
  s = s.strip(" ")
  return s

def parseDoubleCommand(a, b, cmd):
  cmdLenA = len(a)
  cmdLenB = len(b)
  a = cmd.find(a)
  b = cmd.find(b)
  if a > 0 and b > 0:
    # check which one comes first
    if a < b: # a is first
      a = cmd[a+cmdLenA:b] #+len to get rid of command
      b = cmd[b+cmdLenB:]
    else:
      b = cmd[b+cmdLenB:a]
      a = cmd[a+cmdLenA:]
    return [a, b]
  elif a > 0:
    a = cmd[a+cmdLenA:]
    return [a, '']
  elif b > 0:
    b = cmd[b+cmdLenB:]
    return ['', b]

def isProperCmd(cmdReqs, cmd):
  for cmdReq in cmdReqs:
    if cmd.find(cmdReq) < 0:
      return False
  return True
  
class Commander(Thread):
  def __init__(self, fromNumber, cmd):
    self.num = fromNumber
    print "commander number", fromNumber
    self.user = db.Users.find_one({"number":fromNumber})
    print "commander user", self.user
    self.moreText = '(txt "more" to cont)'
    self.cmd = cmd
    Thread.__init__(self)
    
  def mapCommand(self, cmd):
    # parse out command into mode, start, and end
    mode = cmd[0:6]
    # error out if mode is wrong
    regex = re.compile('map [wdp] ', re.IGNORECASE)
    
    if not re.match(regex, mode):
      return {"error": "Map command must be followed by either (w)alking, (d)riving, or (p)ublic transit and a space. ex:map d "}
    elif not isProperCmd(['s:', 'e:'], cmd):
      return {"error": "Map command must have both a (s:)tarting and (e:)nding location, ex:map d s:Seattle e:Portland"}
    else:
      mode = cmd[4]
      if mode == "p":
        # check for departure (d:) or arrival (a:) but not both
        depart = cmd.find("d:")
        arrival = cmd.find("a:")
        if depart >= 0 and arrival >= 0: #both were found, error out
          return {"error":"Transit directions can only have arrival (a:3:00pm) or departure (d:18:00), not both"}
        elif depart < 0 and arrival < 0: #neither was found, error out
          return {"error":"Transit directions must have either arrival (a:3:00pm) or departure (d:18:00)"}
        
        urlTimeType = "Departure" if depart > 0 else "Arrival"
        timeIndex = max(depart, arrival)
        start = cmd.find('s:')
        end = cmd.find('e:')
        # parse out arrival/departure and cut that part out of cmd
        if timeIndex > start and timeIndex > end: # parse until end of cmd
          time = cmd[timeIndex+2:]
          cmd = cmd[:timeIndex]
        elif timeIndex < start and timeIndex < end:
          minIndex = min(start, end)
          time = cmd[timeIndex+2:minIndex]
          cmd = cmd[:timeIndex]+cmd[minIndex:]
        else: # parse until larger start/end is found 
          maxIndex = max(start, end)
          time = cmd[timeIndex+2:maxIndex]
          cmd = cmd[:timeIndex]+cmd[maxIndex:]
    
    [start, end] = parseDoubleCommand('s:', 'e:', cmd)

    # parse out bad things
    badThings = ['"', "'", '\\', ';']
    for bad in badThings:
      start = start.replace(bad, '')
      end = end.replace(bad, '')
      if mode=='p':
        time = time.replace(bad, '')
      
    # convert spaces and put together url
    start = start.replace(' ', '%20')
    end = end.replace(' ', '%20')
    if mode== 'd':
      url = "http://dev.virtualearth.net/REST/V1/Routes/Driving?distanceUnit=mi&wp.0="+start+"&wp.1="+end+"&key="+BING_KEY
    elif mode == 'w':
      url = "http://dev.virtualearth.net/REST/V1/Routes/Walking?distanceUnit=mi&wp.0="+start+"&wp.1="+end+"&key="+BING_KEY
    else: 
      time = time.replace(" ", "%20")
      url = "http://dev.virtualearth.net/REST/V1/Routes/Transit?distanceUnit=mi&wp.0="+start+"&wp.1="+end+"&timeType="+urlTimeType+"&dateTime="+time+"&key="+BING_KEY
      
    try:
      result = simplejson.load(urllib2.urlopen(url))
      parser = BingMapParser(mode)
      res = parser.parse(result)
      return {"success":res}
    except urllib2.HTTPError, e:
      return {"error": "HTTP error: %d" % e.code}
    except urllib2.URLError, e:
      return {"error": "Network error: %s" % e.reason.args[1]} 
  
  def wikiCommand(self, cmd):
    # parse out article title
    replace = [";"]
    for r in replace:
      cmd = cmd.replace(r, "")
    if not isProperCmd(['a:'], cmd):
      return {"error": "Wiki command must have an (a:)rticle specified, ex:wiki a.rabbits"}
    
    [article, section] = parseDoubleCommand('a:', 's:', cmd)
    article = clean(article)
    article = article.replace(' ', '%20')
    section = clean(section)
    
    try:
      request = urllib2.Request("http://en.wikipedia.org/w/index.php?action=render&title="+article)
      request.add_header("User-Agent", 'Gladomus/0.1')
      raw = urllib2.urlopen(request)
      soup = BeautifulSoup(raw)
      # check if its a disambiguation article
      if soup.find('a', {'title':'Help:Disambiguation'}):
        # disambiguation article
        sections = soup.findAll('ul', recursive=False) # fuck it, just doing ul's for now
        num = 1
        res = ""
        for section in sections:
          lists = section.findAll('li', recursive=False)
          for l in lists:
            res = res + str(num)+'.'+''.join(l.findAll(text=True))+' '
            num = num + 1
      else:
        # summary
        if section == '':
          # no section, just grab summary
          summary = soup.find('p', recursive=False)
          textSummary = summary.findAll(text=True)
          res = ''.join(textSummary)
        else:
          # there is a section
          if section == 'toc': #grab table of contents
            tocDiv = soup.find('div', {'id':'toctitle'})
            if tocDiv == None:
              return {'error': 'The article is too short to have a table of contents. Try "wiki a.'+article+'" to get the summary'}
            toc = tocDiv.nextSibling
            toc = toc.findAll(text=True)
            res = ''.join(toc)
          else:
            if isIntOrFloat(section):
              # find by section number
              section = soup.find(text=section).parent.parent['href'][1:]#cut off the '#'
              header = soup.find('span', {'id':section})
              if header == None:
                return {'error': 'The section was not found in the article. Try "wiki a.'+article+' s.toc" to see a table of contents'}
            else:
              headers = soup.findAll(text=re.compile(r'\A'+section, re.IGNORECASE))
              if len(headers) == 0:
                return {'error': 'The section was not found in the article. Try "wiki a.'+article+' s.toc" to see a table of contents'}
              # check to make sure all found headers are spans with class mw-headline
              cleanedHeaders = []
              for header in headers:
                if header.parent.name == 'span':
                  cleanedHeaders.append(header)
              if len(cleanedHeaders) == 0:
                return {'error': 'The section was not found in the article. Try "wiki a.'+article+' s.toc" to see a table of contents'}
              header = cleanedHeader[-1].parent
            p = header.findNext('p')
            res = ''.join(p.findAll(text=True))
            while p.nextSibling and p.nextSibling.nextSibling and p.nextSibling.nextSibling.name == 'p':
              p = p.nextSibling.nextSibling
              res = res +' '+ ''.join(p.findAll(text=True))
      
      return {'success':res}
    except urllib2.HTTPError, e:
      return {"error": "HTTP error: %d" % e.code}
    except urllib2.URLError, e:
      return {"error": "Network error: %s" % e.reason.args[1]} 

  def callCommand(self, cmd):
    originalCmd = cmd
    #cmd = re.sub("\s+", " ", cmd)
    #cmd = cmd.strip(" ")
    replace = ["-", "(", ")", ":", "."]
    for r in replace:
      cmd = cmd.replace(r, "")
    cmd = cmd.split(" ")
    
    currDate = datetime.datetime.utcnow()
    if len(cmd) == 2:
      # call x
      minutes = cmd[1]
    else:
      return {"error": "Call command must be 'call min' (call 5)"}
      
    action = db.Actions()
    action.number = self.num
    action.command = cmd[0]
    action.time = currDate + datetime.timedelta(minuets=minutes)
    action.original = originalCmd
    action.save()
    
    return {'success': "Call has been scheduled"}
    
  def run(self):
		# parses command
    """ 
    call x
    map d s:start e:end
    map p s:start e:end a:arrival/d:departure
    map w s:start e:end
    wiki a:article
    wiki a:article s:toc
    wiki a:article s:section
    *whois x
    *wifi
    more
    help
    s <- search for commands
    """
    cmd = clean(self.cmd)
    cmd = cmd.lower()
    cmdHeader = cmd.split(' ')[0]
    if cmd == 'signup':
      # signup should have been hit in the controller
      return
    elif cmdHeader == 'more':
      self.processMsg('', False)
    elif cmdHeader == "map":
      res = self.mapCommand(cmd)
      if "error" in res:
        self.processMsg(res["error"])
      else:
        msg = ""
        num = 1
        for i in res["success"]:
          msg = msg + str(num)+". "+i["directions"]+i["distance"]+' '
          num = num +1
        self.processMsg(msg)
    #elif cmdHeader == "call":
    #  res = self.callCommand(cmd)
    #  if "error" in res:
    #    self.processMsg(res["error"])
    elif cmdHeader == 'wiki':
      res = self.wikiCommand(cmd)
      if "error" in res:
        self.processMsg(res["error"])
      else:
        self.processMsg(res['success'])
    else:
      res = self.performCustomCommand(cmd)
      if "error" in res:
        self.processMsg(res["error"])
      else:
        self.processMsg(res['success'])
      
  def performCustomCommand(self, cmd):
    cmdHeader = cmd.split(' ')[0]
    # look through custom commands
    customCmds = db.Commands.find({'tested':True, 'cmd':cmdHeader}, {'_id':1})
    
    if customCmds.count() == 0:
      # if no results, error out
      return {'error':cmdHeader+' command not found. Go to www.texatron.com/commands for a list of commands'} #TODO: add suggestions module?
    elif customCmds.count() == 1:
      # if only one custom command returns and user doesnt have that command on their list, add it
      customCmds = list(customCmds)
      if customCmds[0]._id not in self.user.cmds:
        self.user.cmds.append(customCmds[0]._id)
        self.user.save()
      return self.customCommandHelper(customCmds[0]['_id'], cmd)
    # if more than one returns, check user's list
    elif customCmds.count() > 1:
      customList = [ obj['_id'] for obj in list(customCmds)]
      matchCmds = [uCmd for uCmd in self.user.cmds if uCmd in customList]
      #print matchCmds
      # if more than one appears error out
      if len(matchCmds) > 1:
        return {'error': cmdHeader+' has multiple custom commands. Please go to www.texatron.com and select one'} #TODO: make it so you can select one from texting 
      else:
        return self.customCommandHelper(matchCmds[0], cmd)

  def customCommandHelper(self, cmdId, userCmd):
    cmd = db.Commands.find_one({'_id':cmdId})
    # parse out userCmd according to switch operators
    if len(cmd.switches) > 0:
      # there are switches, parse them
      #switchLocs = [s for s in cmd.switches]
      
      switchLocs = []
      switches = []
      #print "switches", cmd.switches
      for s in cmd.switches:
        if s['switch'] != '':
          if userCmd.find(s['switch']+'.') >= 0:
            switchLocs.append({'s':s['switch']+'.', 'loc':userCmd.find(s['switch']+'.')})
          elif  s['default'] != '':
            switches.append({'s':s['switch']+'.', 'data':s['default']})
          else:
            return {'error':'Error:missing '+s['switch']+' switch. ex:'+cmd.example}
        
      #sort by locs
      switchLocs = sorted(switchLocs, key=itemgetter('loc'))
      for i in xrange(len(switchLocs)-1):
        s1 = switchLocs[i]
        s2 = switchLocs[i+1]
        data = clean(userCmd[s1['loc']+2:s2['loc']]).replace(' ', '%20')
        switches.append({'s':s1['s'], 'data':data})
      # append final one
      if len(switchLocs) > 0:
        data = clean(userCmd[switchLocs[-1]['loc']+2:]).replace(' ', '%20')
        switches.append({'s':switchLocs[-1]['s'],'data':data})

      url = cmd.url
      #put together url with switches
      for s in switches:
        print s['data']
        newUrl = url.replace('{'+s['s'][:-1]+'}', s['data'])
        if newUrl == url:
          # something went wrong. a command didnt get replaced
          return {'error':"Error:couldn't find switch "+s['s']+""}
        else:
          url = newUrl
    else:
      url = cmd.url
    try:
      print url
      request = urllib2.Request(url)
      request.add_header("User-Agent", 'Texatron/0.1')
      raw = urllib2.urlopen(request)
      soup = BeautifulSoup(raw)
      # parse soup according to includes
      msg = ''
      count = 1
      includeText = self.findHtmlElements(soup, cmd.includes)
      excludeText = self.findHtmlElements(soup, cmd.excludes)

      if len(excludeText) > 0:
        text = [included for included in includeText if included not in excludeText]
      else:
        text = includeText
      
      if cmd.enumerate:
        for t in text:
          msg = msg + ' '+str(count)+'.'+ str(t.encode("utf-8"))
          count = count + 1
      else:
        msg = ''.join(text)
      return {'success':msg}
    except urllib2.HTTPError, e:
      return {"error": "HTTP error: %d" % e.code}
    except urllib2.URLError, e:
      return {"error": "Network error: %s" % e.reason.args[1]} 

  def findHtmlElements(self, soup, elementsToFind):
    foundText = []
    for i in elementsToFind:
      # put together tag matches dict
      matchDict = {}
      for match in i['matches']:
        matchDict[match['type']] = re.compile(r'\b%s\b'%match['value'])
      found = soup.findAll(i['tag'], matchDict)
      
      for f in found:
        foundText = foundText + f.findAll(text=True)
    return foundText

  def processMsg(self, msg, isNewMsg=True, cache=True):
    print "process Msg", msg
    if cache:
      # CACHE RES
      cacheNumber = db.cache.find_one({'number':self.num})
      currDate = datetime.datetime.utcnow()
      index = 160*MAX_TEXTS-len(self.moreText)
      if cacheNumber and isNewMsg:
        # update cache
        db.cache.update({'number':self.num}, {'$set':{'data':msg, 'index':index, 'time':currDate}})
      elif not isNewMsg:# old message, move cache index
        msg = cacheNumber['data']
        index = cacheNumber['index']
        if (index > len(msg)):
          return # break out
        msg = msg[index:]
        # move cache index to new place, send off message
        db.cache.update({'number':self.num}, {'$set':{'index':max(len(msg), index+160*MAX_TEXTS)}})
      else: # new cache for that number
        cache = db.Cache()      
        cache.number = unicode(self.num)
        cache.data = unicode(msg, errors='ignore')
        cache.index = index
        cache.time = currDate
        cache.save()
    i = 0
    while i*160 < len(msg) and i<MAX_TEXTS:
      print "sending msg"
      if self.user.freeMsg > 0:
        self.user.freeMsg = self.user.freeMsg - 1
      elif self.user.paidMsg > 0:
        self.user.paidMsg = self.user.paidMsg - 1
      else:
        CLIENT.sms.messages.create(to=self.num, from_=TWILIO_NUM, body = "You have used up your texts. Buy more at www.textatron.com")
        break
        
      if i+1 >= MAX_TEXTS and len(msg) > (i+1)*160:
        CLIENT.sms.messages.create(to=self.num, from_=TWILIO_NUM, body = msg[i*160:(i+1)*160-len(self.moreText)]+self.moreText)
        #print self.msg[i*160:(i+1)*160-len(self.moreText)]+self.moreText
      elif (i+1)*160 <= len(msg):
        CLIENT.sms.messages.create(to=self.num, from_=TWILIO_NUM, body = msg[i*160:(i+1)*160])
        #print self.msg[i*160:(i+1)*160]
      else:
        CLIENT.sms.messages.create(to=self.num, from_=TWILIO_NUM, body = msg[i*160:])
        #print self.msg[i*160:]

      self.user.save()
      i = i + 1
      #sleep 1.5 seconds
      if i < len(msg):
        time.sleep(1.5)
        
    log('text', self.num+':'+str(unicode(msg, errors='ignore')))
