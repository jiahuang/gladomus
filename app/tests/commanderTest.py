import sys
sys.path.append("../")
from commander import Commander

class CommanderTest:
  def __init__(self):
    self.c = Commander()
  
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
      if "error" not in res:
        # error out
        testRes = "Broke on: "+badCmd+"\n Res:"+str(res)+'\n'
        print testRes
        
    # good commands: these should not 404 or return errors
    cmds = ["Map d s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84",
    "Map w s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84", 
    "Map p d:10:40PM s:4714 17th Ave NE, Seattle e:Microsoft Buildling 84",
    "Map p e:Microsoft Buildling 84 d:10:40 s:4714 17th Ave NE, Seattle", 
    "Map p e:Microsoft Buildling 84 a:10:40AM s:4714 17th Ave NE, Seattle",
    "Map p e:Microsoft Buildling 84 s:4714 17th Ave NE, Seattle a:10:40"]
    for cmd in cmds:
      res = self.c.mapCommand(cmd)
      if "error" in res:
        # error out
        testRes = "Broke on: "+cmd+"\n Res:"+str(res)+'\n'
        print testRes
    print "=== end of MapTest ===\n"

def main(name):
  tester = CommanderTest()
  tester.mapTest()

if __name__ == '__main__':
  main(*sys.argv)
