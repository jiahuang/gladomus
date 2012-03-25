import sys
sys.path.append("../app/")
from models import db
from twilio.rest import TwilioRestClient
import datetime
import logger.log

class actionDaemon:
	def performActions():
		# grab all open actions
		actions = db.actions.find()
		time = datetime.datetime.utcnow()
		account_sid = "ACXXXXXXXXXXXXXXXXX"
		auth_token = "YYYYYYYYYYYYYYYYYY"
		client = TwilioRestClient(account_sid, auth_token)
 
		for action in actions:
			if action['command'] == 'help' and action['time'] < time:
				# send off a call
				# Get these credentials from http://twilio.com/user/account
				
				# Make the call
				call = client.calls.create(to="+1"+action['number'],  # Any phone number
					from_="+12125551234", # Must be a valid Twilio number
          url="http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient")
          # make sure url displays nothing. then call auto hangs up. 
				log('actionDaemon', call.sid)
