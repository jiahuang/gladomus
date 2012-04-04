from models import *
from twilio.rest import TwilioRestClient
from time import gmtime, strftime
import urllib2
import simplejson
from bingMapParser import BingMapParser
import re
from logger import log
from BeautifulSoup import BeautifulSoup

class Commander:
  def __init__(self):
    self.client = TwilioRestClient(TWILIO_SID, TWILIO_AUTH)

  def mapCommand(self, cmd):
    # parse out command into mode, start, and end
    mode = cmd[0:6]
    # error out if mode is wrong
    regex = re.compile('map [wdp] ', re.IGNORECASE)
    
    if not re.match(regex, mode):
      return {"error": "Map command must be followed by either w, d, or p and a space. ex:map p "}
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
    
    start = cmd.find('s:')
    end = cmd.find('e:')
    # check which one comes first
    if start < end: # start is first
      start = cmd[start+2:end] #+2 to get rid of s:
      end = cmd[end+2:]
    else:
      end = cmd[end+2:start]
      start = cmd[start+2:]
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
    cmd = cmd.split(' ')
    title = '%20'.join(cmd[1:])
    try:
      request = urllib2.Request("http://en.wikipedia.org/w/index.php?action=render&title="+title)
      request.add_header("User-Agent", 'Gladomus/0.1')
      raw = urllib2.urlopen(request)
      soup = BeautifulSoup(raw)
      # check if its a disambiguation article
      if not soup.find('table', {'class':'infobox'}):
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
        summary = soup.find('p', recursive=False)
        textSummary = summary.findAll(text=True)
        res = ''.join(textSummary)
    
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
    cmd = re.sub("\s+", " ", cmd)
    cmd = cmd.strip(" ")
    cmd = cmd.lower()
    cmdHeader = cmd.split(' ')[0]
    if cmdHeader == "map":
      res = self.mapCommand(cmd)
      if "error" in res:
        self.sendMsg(res["error"], fromNumber)
      else:
        #parse out messages into 140 chars and send
        msg = ""
        num = 1
        for i in res["success"]:
          msg = msg + str(num)+". "+i["directions"]+i["distance"]+' '
          num = num +1
        self.sendMsg(msg, fromNumber)
    elif cmdHeader == "call":
      res = self.callCommand(cmd, fromNumber)
      if "error" in res:
        self.sendMsg(res["error"], fromNumber)
    elif cmdHeader == 'wiki':
      res = self.wikiCommand(cmd)
      if "error" in res:
        self.sendMsg(res["error"], fromNumber)
      else:
        self.sendMsg(res['success'], fromNumber)

  def sendMsg(self, msg, number):
    i = 0
    while i < len(msg):
      if i+160 <= len(msg):
        self.client.sms.messages.create(to=number, from_="+1"+TWILIO_NUM, body = msg[i:i+160])
      else:
          self.client.sms.messages.create(to=number, from_="+1"+TWILIO_NUM, body = msg[i:])
      i = i + 160
    #message = self.client.sms.messages.create(to=number, from_="+1"+TWILIO_NUM, body=msg)
    log('text', number+':'+msg)


