import sys
sys.path.append("../app/")
from models *
from twilio.rest import TwilioRestClient
import datetime
import logger.log

class actionDaemon:
  def performCalls(self):
    time = datetime.datetime.utcnow()
		actions = db.actions.find({'cmd':'call', 'time':{'$lte':time})
		client = TwilioRestClient(TWILIO_SID, TWILIO_AUTH)
 
		for action in actions:
			if action['command'] == 'help' and action['time'] < time:
				# send off a call
				
				# Make the call
        call = client.calls.create(to="+1"+action['number'],  # Any phone number
					from_="+1"+TWILIO_NUM, 
          url="http://getouttahere.me/hangup")
				log('actionDaemon', call.sid)
        
	def performActions(self):
		self.performCalls()
