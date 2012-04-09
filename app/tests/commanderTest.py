import sys
sys.path.append("../")
from models import *
from commander import Commander
import time

class CommanderTest:
  def __init__(self):
    self.c = Commander('+19193971139')

  def printResults(self, cmd, res, good=True, printRes=False):
    if good:
      if "error" in res:
        # error out
        testRes = "Broke on: "+cmd+"\n Res:"+str(res)+'\n'
        print testRes
      if printRes:
        print res['success']
    else:
      if "error" not in res:
        # error out
        testRes = "Broke on: "+cmd+"\n Res:"+str(res)+'\n'
        print testRes
      if printRes:
        print res['error']
  
  def wikiTest(self):
    print "=== start of WikiTest ===\n"
    badCmds = ["wiki slkdfjslkdfj", 'wiki a:sldfksjdf', 'wiki s:3sdf', 
    'wiki a:apple s:sdfes', 'wiki a:rusko s:name']
    for badCmd in badCmds:
      res = self.c.wikiCommand(badCmd)
      self.printResults(badCmd, res, False)
        
    cmds = ['wiki a:apple', 'wiki   a: mad cow      ', 
    'wiki a:wiz', 'wiki a:Christopher', 'wiki a:wiz s:sdfsdf',
    'wiki a:rabbit s:1', 'wiki a:bill gates s:2.6', 'wiki a:rusko']
    for cmd in cmds:
      res = self.c.wikiCommand(cmd)
      self.printResults(cmd, res)
          
  def mapTest(self):
    print "=== start of MapTest ===\n"
    # bad commands: these should all return errors
    badCmds = ["Map s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84", 
    "Map ds:4714 17th Ave NE, Seattle e:Microsoft Buildling 84",
    "Map p s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84", 
    "Map p s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84 a:sdlkfjsdf",
    "Map p s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84 a:10:40 d:10:40"]
    for badCmd in badCmds:
      res = self.c.mapCommand(badCmd)
      self.printResults(badCmd, res, False)
        
    # good commands: these should not 404 or return errors
    cmds = ["Map d s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84",
    "Map w s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84", 
    "Map p d:10:40PM s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84",
    "Map p e:Microsoft Buildling 84 d:10:40 s:4714 17th Ave NE, Seattle", 
    "Map p e:Microsoft Buildling 84 a:10:40AM s:4714 17th Ave NE, Seattle",
    "Map p e:Microsoft Buildling 84 s:4714 17th Ave NE, Seattle a:10:40"]
    
    for cmd in cmds:
      res = self.c.mapCommand(cmd)
      self.printResults(cmd, res)
    print "=== end of MapTest ===\n"

  def parseTester(self):
    cmds = ['wiki a:apple']#, 'wiki a:pear', 'map d s:4714 17th Ave NE, Seattle e:Microsoft Building 84, WA']
    for cmd in cmds:
      self.c.parseCommand(cmd, '+19193971139')

  def moreTest(self):
    self.c.parseCommand('wiki a:pear', '+19193971139')
    time.sleep(1.5*4)
    self.c.parseCommand('more', '+19193971139')

  def customCommandTest(self):
    print "=== start of custom command test ===\n"
    # assumes that commands are populated with things in populateCmds.py
    badCmds = ["sdf", 'woo', 'g', 'g test' 'gh user proj']
    for badCmd in badCmds:
      res = self.c.performCustomCommand(badCmd)
      self.printResults(badCmd, res, False, True)

    cmds = ['woot', 'reddit', 'hn', 'g s.test', 'g s.jialiya huang', 'gh p.hireAnOliner u.jiahuang',
    'gh u.jiahuang p.hireAnOliner', 'gh']
    for cmd in cmds:
      res = self.c.performCustomCommand(cmd)
      print res
      self.printResults(cmd, res, True, True)

    print "=== end of custom command test ===\n"


def main(name):
  tester = CommanderTest()
  #tester.mapTest()
  #tester.wikiTest()
  #tester.parseTester()
  #tester.moreTest()
  tester.customCommandTest()

if __name__ == '__main__':
  main(*sys.argv)
