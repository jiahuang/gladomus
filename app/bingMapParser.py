# parses out the results from bing maps
# allows for driving, public transit, and walking directions

import urllib2
import simplejson
import re
import datetime

class BingMapParser:
  def __init__(self, mode):
    self.mode = mode
  
  def parse(self, item):
    """
      returns the following
      directions[]
        {text: directions, time:#min}
      #result[0]['instruction']['text']
      #result['resourceSets'][0]['resources'][0]['routeLegs'][0]['itineraryItems'][0]['instruction']['text']#['travelDistance']
    """
    res = []
    itinerary = item['resourceSets'][0]['resources'][0]['routeLegs'][0]['itineraryItems']
    if self.mode not in ['w', 'd', 'p']:
      raise Exception("map mode needs to be either 'w'alking, 'd'riving, or 'p'ublic transit. map w, map d, or map p")
      
    # walking or driving
    for i in itinerary:
      directions = i['instruction']['text']
      distance = '('+str(round(i['travelDistance'], 2))+' mi)'
      resItem = {'directions':directions, 'distance':distance}
      res.append(resItem)
      # CHECK FOR CHILD ITINERARY when you're on a bus
      if self.mode == "p" and "childItineraryItems" in i:
        # its a bus
        for child in i["childItineraryItems"]:
          directions = child['instruction']['text']
          # fuck everything about this
          time = child['time'] # given as this: "time":"\/Date(1320187586000-0700)\/"
          # parse out slashes
          newTime = time[time.find('(')+1:time.find(')')]
          # check if its gmt + or -
          if '+' in newTime:
            # split along +
            newTime = newTime.split('+')
            newTime[1] = newTime[1].lstrip('0') #strip all beginning zeros
            time = datetime.datetime.utcfromtimestamp(int(newTime[0])/1000 + int(newTime[1])*6*6).time()#divide by 100 because time is 700 instead of 7
          else:
            # split along -
            newTime = newTime.split('-')
            newTime[1] = newTime[1].lstrip('0') #strip all beginning zeros
            time = datetime.datetime.utcfromtimestamp(int(newTime[0])/1000 - int(newTime[1])*6*6).time()#divide by 100 because time is 700 instead of 7
            
          distance = '('+str(time.hour)+':'+str(time.minute)+')'# in min not miles
          resItem = {'directions':directions, 'distance':distance}
          res.append(resItem)
    return res
