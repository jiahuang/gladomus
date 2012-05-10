from multiprocessing import Process
import time

def f(name):
    for i in range(10):
      print "process:"+str(i)
      time.sleep(1)

if __name__ == '__main__':
  for i in range(3):
    p = Process(target=f, args=('bob',))
    p.start()
    #p.join()
