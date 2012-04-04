''' Logging files '''
import sys
import datetime

def log(process, item):
	# write data to a file
	now = datetime.datetime.now()
	filename = 'glad:'+process+'_'+str(now.month)+'-'+str(now.day)+'.log'
	f = open(filename, 'a')
	f.write(str(now)+": "+item.encode('utf-8')+'\n')
	f.close()
