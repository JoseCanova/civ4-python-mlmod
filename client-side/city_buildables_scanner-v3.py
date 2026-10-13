# city_buildables_scanner.py
# Python 2.4 & Python 3 Universal Compatible City Buildables Scanner for Civilization IV

import sys
from CvPythonExtensions import CyGlobalContext
import http_request_manager

gc = CyGlobalContext()


class CityBuildablesScanner(object):
    """
    Scans all cities of the active human player on each turn, retrieving
    available units/troops and buildings along with their hammer production costs.
    Delegates JSON telemetry submission to HttpRequestManager.
    """

    def __init__(self, host="localhost", port=8000, api_endpoint="/api", http_mgr=None):
        if http_mgr is not None:
            self.http_mgr = http_mgr
        else:
            self.http_mgr = http_request_manager.HttpRequestManager(
                host=host,
                port=port,
                default_endpoint=api_endpoint
            )

    def getUnitCost(self, pCity, pPlayer, iUnit, unitInfo):
        """Retrieves hammer cost for training a unit for this player."""
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
        """Retrieves hammer cost for constructing a building for this player."""
        iCost = 0
        if pPlayer and hasattr(pPlayer, 'getBuildingProductionNeeded'):
            try:
                iCost = pPlayer.getBuildingProductionNeeded(iBuilding)
            except Exception:
                iCost = 0

        if iCost <= 0 and buildingInfo and hasattr(buildingInfo, 'getBuildingCost'):
            try:
                iCost = buildingInfo.getBuildingCost(iBuilding)
            except Exception:
                iCost = 0

        if iCost <= 0 and buildingInfo and hasattr(buildingInfo, 'getProductionCost'):
            try:
                iCost = buildingInfo.getProductionCost()
            except Exception:
                iCost = 0

        return iCost

    def getAvailableUnitsForCity(self, pCity, pPlayer):
        units_list = []
        iNumUnits = gc.getNumUnitInfos()
        for iUnit in range(iNumUnits):
            if pCity.canTrain(iUnit, False, True):
                unitInfo = gc.getUnitInfo(iUnit)
                if unitInfo:
                    szType = unitInfo.getType()
                    iCost = self.getUnitCost(pCity, pPlayer, iUnit, unitInfo)
                    units_list.append({
                        "type": szType,
                        "cost": iCost
                    })
        return units_list

    def getAvailableBuildingsForCity(self, pCity, pPlayer):
        buildings_list = []
        iNumBuildings = gc.getNumBuildingInfos()
        for iBuilding in range(iNumBuildings):
            if pCity.canConstruct(iBuilding, False, True, False):
                buildingInfo = gc.getBuildingInfo(iBuilding)
                if buildingInfo:
                    szType = buildingInfo.getType()
                    iCost = self.getBuildingCost(pCity, pPlayer, iBuilding, buildingInfo)
                    buildings_list.append({
                        "type": szType,
                        "cost": iCost
                    })
        return buildings_list

    def scanActivePlayerCities(self, pPlayer=None):
        if pPlayer is None:
            pPlayer = gc.getActivePlayer()

        if not pPlayer or pPlayer.isNone():
            return None

        if not pPlayer.isHuman():
            return None

        iPlayerID = pPlayer.getID()
        pGame = gc.getGame()
        if pGame:
            iGameTurn = pGame.getGameTurn()
        else:
            iGameTurn = 0

        cities_data = []

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
        if not payload or not self.http_mgr:
            return False

        return self.http_mgr.send_post(payload)

    def run_turn_scan(self, pPlayer=None):
        payload = self.scanActivePlayerCities(pPlayer)
        if payload:
            return self.send_telemetry(payload)
        return False
