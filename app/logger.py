''' Logging files '''
import sys
import datetime

def log(process, item):
	# write data to a file
	now = datetime.datetime.now()
	filename = 'get-'+process+'-'+str(now.day)+'.log'
	f = open(filename, 'a')
	f.write(str(now)+": "+str(item))
	f.close()
