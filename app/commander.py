from models import *
from twilio.rest import TwilioRestClient
from time import gmtime, strftime
import urllib2
import simplejson
from bingMapParser import BingMapParser
import re
from logger import log
from BeautifulSoup import BeautifulSoup
import time
from threading import Thread

CLIENT = TwilioRestClient(TWILIO_SID, TWILIO_AUTH)

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
  
class Commander:
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
  
  def wikiCommand(self, cmd, fromNumber):
    # parse out article title
    replace = [";"]
    for r in replace:
      cmd = cmd.replace(r, "")
    if not isProperCmd(['a:'], cmd):
      return {"error": "Wiki command must have an (a:)rticle specified, ex:wiki a:rabbits"}
    
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
              return {'error': 'The article is too short to have a table of contents. Try "wiki a:'+article+'" to get the summary'}
            toc = tocDiv.nextSibling
            toc = toc.findAll(text=True)
            res = ''.join(toc)
          else:
            if isIntOrFloat(section):
              # find by section number
              section = soup.find(text=section).parent.parent['href'][1:]#cut off the '#'
              header = soup.find('span', {'id':section})
              if header == None:
                return {'error': 'The section was not found in the article. Try "wiki a:'+article+' s:toc" to see a table of contents'}
            else:
              headers = soup.findAll(text=re.compile(r'\A'+section, re.IGNORECASE))
              if len(headers) == 0:
                return {'error': 'The section was not found in the article. Try "wiki a:'+article+' s:toc" to see a table of contents'}
              # check to make sure all found headers are spans with class mw-headline
              cleanedHeaders = []
              for header in headers:
                if header.parent.name == 'span':
                  cleanedHeaders.append(header)
              if len(cleanedHeaders) == 0:
                return {'error': 'The section was not found in the article. Try "wiki a:'+article+' s:toc" to see a table of contents'}
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

  def callCommand(self, cmd, fromNumber):
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
      number = fromNumber
      minutes = cmd[1]
    elif len(cmd) == 3:
      # call #n x
      number = cmd[1]
      minutes = cmd[2]
    else:
      return {"error": "Call command must be either 'call min' (call 5) or 'call number min' (call 0000000000 5)"}
      
    action = db.Actions()
    action.number = number
    action.command = cmd[0]
    action.time = currDate + datetime.timedelta(minuets=minutes)
    action.original = originalCmd
    action.save()
    
    return {'Success': "Call has been scheduled"}
    
  def parseCommand(self, cmd, fromNumber):
		# parses command
    """ 
    call x
    call #n x
    txt x msg
    txt #n x msg
    map d s:start e:end
    map p s:start e:end a:arrival/d:departure
    map w s:start e:end
    wiki title
    whois x
    """
    cmd = clean(cmd)
    cmd = cmd.lower()
    cmdHeader = cmd.split(' ')[0]
    if cmdHeader == "map":
      res = self.mapCommand(cmd)
      if "error" in res:
        sendMsg(res["error"], fromNumber)
      else:
        msg = ""
        num = 1
        for i in res["success"]:
          msg = msg + str(num)+". "+i["directions"]+i["distance"]+' '
          num = num +1
        self.processMsg(msg, fromNumber)
    elif cmdHeader == "call":
      res = self.callCommand(cmd, fromNumber)
      if "error" in res:
        self.processMsg(res["error"], fromNumber)
    elif cmdHeader == 'wiki':
      res = self.wikiCommand(cmd, fromNumber)
      if "error" in res:
        self.processMsg(res["error"], fromNumber)
      else:
        self.processMsg(res['success'], fromNumber)
  
  def processMsg(self, msg, number, cache=True):
    Sender(msg, number, cache).start()
    
class Sender(Thread):
  def __init__(self, msg, number, cache):
    self.msg = msg
    self.number = number
    self.moreText = '(txt "more" to cont)'
    self.cache = cache
    Thread.__init__(self)
  
  def run(self):
    i = 0
    maxTexts = 4 # max number before delaying into more
    
    if self.cache:
      # CACHE RES
      cache = db.Cache()
      cache.number = unicode(self.number)
      cache.data = self.msg
      cache.index = 160*maxTexts-len(self.moreText)
      cache.time = datetime.datetime.utcnow()
      cache.save()
    
    while i*160 < len(self.msg) and i<maxTexts:
      if i+1 >= maxTexts:
        #CLIENT.sms.messages.create(to=self.number, from_="+1"+TWILIO_NUM, body = self.msg[i*160:(i+1)*160-len(self.moreText)]+self.moreText)
        print self.msg[i*160:(i+1)*160-len(self.moreText)]+self.moreText
      elif (i+1)*160 <= len(self.msg):
        #CLIENT.sms.messages.create(to=self.number, from_="+1"+TWILIO_NUM, body = self.msg[i*160:(i+1)*160])
         print self.msg[i*160:(i+1)*160]
      else:
        #CLIENT.sms.messages.create(to=self.number, from_="+1"+TWILIO_NUM, body = self.msg[i*160:])
        print self.msg[i*160:]
      i = i + 1
      #sleep 1.5 seconds
      if i < len(self.msg):
        time.sleep(1.5)
        
    log('text', self.number+':'+self.msg)
