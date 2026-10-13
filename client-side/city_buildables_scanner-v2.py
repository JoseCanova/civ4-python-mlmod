# city_buildables_scanner.py
# Python 2.4 & Python 3 Universal Compatible City Buildables Scanner for Civilization IV

import sys
import socket

from CvPythonExtensions import CyGlobalContext

try:
    import httplib
except ImportError:
    try:
        import http.client as httplib
    except ImportError:
        httplib = None

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = None

gc = CyGlobalContext()

class CityBuildablesScanner(object):
    """
    Scans all cities of the active human player on each turn, retrieving
    available units/troops and buildings along with their hammer production costs.
    Serializes and submits JSON telemetry to http://localhost:8000/api using XML Type keys.
    Strictly compatible with Python 2.4 syntax and Civ IV Boost.Python API.
    """
    def __init__(self, host="localhost", port=8000, api_endpoint="/api"):
        self.host = host
        self.port = port
        self.api_endpoint = api_endpoint

    def getUnitCost(self, pCity, pPlayer, iUnit, unitInfo):
        """
        Retrieves the required hammer production cost for a unit for this player.
        Uses CyPlayer.getUnitProductionNeeded(iUnit) or CvUnitInfo.getProductionCost().
        """
        iCost = 0
        if pPlayer and hasattr(pPlayer, 'getUnitProductionNeeded'):
            try:
                iCost = pPlayer.getUnitProductionNeeded(iUnit)
            except Exception:
                iCost = 0

        if iCost <= 0 and unitInfo and hasattr(unitInfo, 'getProductionCost'):
            try:
                iCost = unitInfo.getProductionCost()
            except Exception:
                iCost = 0

        return iCost

    def getBuildingCost(self, pCity, pPlayer, iBuilding, buildingInfo):
        """
        Retrieves the required hammer production cost for a building for this player.
        Uses CyPlayer.getBuildingProductionNeeded(iBuilding) or CvBuildingInfo.getProductionCost().
        """
        iCost = 0
        if pPlayer and hasattr(pPlayer, 'getBuildingProductionNeeded'):
            try:
                iCost = pPlayer.getBuildingProductionNeeded(iBuilding)
            except Exception:
                iCost = 0

        if iCost <= 0 and buildingInfo and hasattr(buildingInfo, 'getProductionCost'):
            try:
                iCost = buildingInfo.getProductionCost()
            except Exception:
                iCost = 0

        return iCost

    def getAvailableUnitsForCity(self, pCity, pPlayer):
        """
        Retrieves a list of dictionaries for all units the city can train.
        Uses XML Type string (e.g. 'UNIT_WARRIOR') instead of integer ID.
        """
        units_list = []
        iNumUnits = gc.getNumUnitInfos()
        for iUnit in range(iNumUnits):
            # canTrain(iUnit, bContinue, bTestVisible)
            if pCity.canTrain(iUnit, False, True):
                unitInfo = gc.getUnitInfo(iUnit)
                if unitInfo:
                    szType = unitInfo.getType()  # XML Type Key (e.g., 'UNIT_SETTLER')
                    iCost = self.getUnitCost(pCity, pPlayer, iUnit, unitInfo)
                    
                    units_list.append({
                        "type": szType,
                        "cost": iCost
                    })
        return units_list

    def getAvailableBuildingsForCity(self, pCity, pPlayer):
        """
        Retrieves a list of dictionaries for all buildings the city can construct.
        Uses XML Type string (e.g. 'BUILDING_GRANARY') instead of integer ID.
        """
        buildings_list = []
        iNumBuildings = gc.getNumBuildingInfos()
        for iBuilding in range(iNumBuildings):
            # canConstruct(iBuilding, bContinue, bTestVisible, bIgnoreCost)
            if pCity.canConstruct(iBuilding, False, True, False):
                buildingInfo = gc.getBuildingInfo(iBuilding)
                if buildingInfo:
                    szType = buildingInfo.getType()  # XML Type Key (e.g., 'BUILDING_BARRACKS')
                    iCost = self.getBuildingCost(pCity, pPlayer, iBuilding, buildingInfo)
                    
                    buildings_list.append({
                        "type": szType,
                        "cost": iCost
                    })
        return buildings_list

    def scanActivePlayerCities(self, pPlayer=None):
        """
        Scans all cities belonging to the given or active human player.
        Returns a structured dictionary ready for JSON serialization.
        """
        if pPlayer is None:
            pPlayer = gc.getActivePlayer()

        if not pPlayer or pPlayer.isNone():
            return None

        # Ensure player is active/human
        if not pPlayer.isHuman():
            return None

        iPlayerID = pPlayer.getID()
        pGame = gc.getGame()
        
        # Python 2.4 compliant if/else block
        if pGame:
            iGameTurn = pGame.getGameTurn()
        else:
            iGameTurn = 0

        cities_data = []

        # Iterate over all cities owned by the player
        (pCity, iter_val) = pPlayer.firstCity(False)
        while pCity and not pCity.isNone():
            cityName = pCity.getName()
            iCityID = pCity.getID()

            available_units = self.getAvailableUnitsForCity(pCity, pPlayer)
            available_buildings = self.getAvailableBuildingsForCity(pCity, pPlayer)

            city_entry = {
                "name": cityName,
                "id": iCityID,
                "available_units": available_units,
                "available_buildings": available_buildings
            }
            cities_data.append(city_entry)

            (pCity, iter_val) = pPlayer.nextCity(iter_val, False)

        payload = {
            "event": "onCityBuildablesScan",
            "turn": iGameTurn,
            "player_id": iPlayerID,
            "cities_count": len(cities_data),
            "cities": cities_data
        }

        return payload

    def send_telemetry(self, payload):
        """
        Sends the JSON payload to the HTTP server at host:port/api using UTF-8 encoding.
        Uses Python 2.4 nested try-except-finally blocks for safe execution.
        """
        if not payload or httplib is None or json is None:
            return False

        old_timeout = None
        if hasattr(socket, 'getdefaulttimeout'):
            old_timeout = socket.getdefaulttimeout()
        if hasattr(socket, 'setdefaulttimeout'):
            socket.setdefaulttimeout(20.0)

        try:
            try:
                # Serialize to UTF-8 JSON
                json_str = json.dumps(payload, ensure_ascii=False)
                if hasattr(json_str, 'encode'):
                    json_bytes = json_str.encode('utf-8')
                else:
                    json_bytes = str(json_str)

                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Length": str(len(json_bytes))
                }

                conn = httplib.HTTPConnection(self.host, self.port)
                conn.request("POST", self.api_endpoint, json_bytes, headers)
                response = conn.getresponse()
                conn.close()

                print "CityBuildablesScanner: POST to %s returned status %d" % (
                    self.api_endpoint, response.status
                )
                if response.status in (200, 201, 202, 204):
                    return True
                else:
                    return False
            except Exception:
                e = sys.exc_info()[1]
                print "CityBuildablesScanner Warning: Failed to post buildables telemetry (%s)" % str(e)
                return False
        finally:
            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(old_timeout)

    def run_turn_scan(self, pPlayer=None):
        """
        Main execution entry point to be called each turn.
        Optionally accepts pPlayer instance.
        """
        payload = self.scanActivePlayerCities(pPlayer)
        if payload:
            return self.send_telemetry(payload)
        return False
