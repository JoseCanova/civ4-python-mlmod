import city_buildables_scanner
from CvPythonExtensions import CyGlobalContext



gc = CyGlobalContext()


print "Hello"

iPlayer = gc.getActivePlayer()
buildables_scanner = city_buildables_scanner.CityBuildablesScanner(
            host="localhost",
            port=8000,
            api_endpoint="/api")
print iPlayer
if iPlayer and not iPlayer.isNone():
     if iPlayer.isHuman():
        print "=== [EVENT] Turn %d started for Human Player (%s) ===" % (2, iPlayer.getCivilizationShortDescription(0))
        try:
            buildables_scanner.run_turn_scan(iPlayer)
        except Exception, e:
            print "Warning: Failed running buildables scan on turn %d: %s" % (2, str(e))
     else:
        print "no human player"
