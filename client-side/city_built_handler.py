# city_built_handler.py
# Python 2.4 Compatible Delegate Handler for Civ IV City Built Events

from CvPythonExtensions import CyGlobalContext

gc = CyGlobalContext()


class CityBuiltDelegate(object):
    """
    Delegate helper class that manages the strategic behavior and telemetry payload
    when a new city is founded (onCityBuilt event).
    Separates event dispatching from gameplay logic and strategy determination.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self, http_mgr=None):
        self.http_mgr = http_mgr

    def determine_city_strategy(self, pCity, pPlayer):
        """
        Determines the operational strategy for a newly built city.
        Checks forge / specialist availability for specialist emphasis (e.g. ENGINEER_HUB).
        Uses strict Python 2.4 if/else blocks - NO ternary operators.
        """
        if not pCity or pCity.isNone():
            return None

        cityName = pCity.getName()

        # Check if Forge building exists to enable Engineer specialist allocation
        iForgeType = gc.getInfoTypeForString("BUILDING_FORGE")
        bHasForge = False
        if iForgeType != -1 and hasattr(pCity, "isHasBuilding"):
            bHasForge = pCity.isHasBuilding(iForgeType)

        specialistPriority = []
        if bHasForge:
            specialistPriority = ["SPECIALIST_ENGINEER"]

        iNumCities = 1
        if pPlayer and hasattr(pPlayer, "getNumCities"):
            iNumCities = pPlayer.getNumCities()

        # Strategy selection logic using explicit Python 2.4 if/else blocks
        if iNumCities == 1:
            szStrategy = "GROWTH"
            yieldPriority = ["FOOD", "COMMERCE", "PRODUCTION"]
            specialistPriority = []
            firstBuild = "BUILDING_GRANARY"
        elif hasattr(pCity, "isCoastal") and pCity.isCoastal(10):
            szStrategy = "COMMERCE"
            yieldPriority = ["COMMERCE", "FOOD", "PRODUCTION"]
            specialistPriority = []
            firstBuild = "BUILDING_LIGHTHOUSE"
        elif bHasForge:
            szStrategy = "ENGINEER_HUB"
            yieldPriority = ["FOOD", "PRODUCTION", "COMMERCE"]
            specialistPriority = ["SPECIALIST_ENGINEER"]
            firstBuild = "BUILDING_FORGE"
        else:
            szStrategy = "PRODUCTION"
            yieldPriority = ["PRODUCTION", "FOOD", "COMMERCE"]
            specialistPriority = []
            firstBuild = "BUILDING_BARRACKS"

        strategy_payload = {
            "strategy": {
                "type": szStrategy,
                "yield_priority": yieldPriority,
                "specialist_priority": specialistPriority,
                "recommended_first_build": firstBuild,
                "min_food_buffer": 2,
                "auto_manage_citizens": True
            }
        }

        return strategy_payload

    def handle_city_built(self, pCity, argsList):
        """
        Executes the behavior when onCityBuilt is delegated from CustomCiv4EventHandler.
        Calculates city strategy and posts JSON telemetry to HTTP server.
        """
        if not pCity or pCity.isNone():
            return False

        cityName = pCity.getName()
        iOwner = pCity.getOwner()

        pPlayer = None
        if hasattr(gc, "getPlayer"):
            pPlayer = gc.getPlayer(iOwner)

        # Determine strategy payload
        strategy_data = self.determine_city_strategy(pCity, pPlayer)

        szStrategy = "DEFAULT"
        if strategy_data:
            if "strategy" in strategy_data:
                szStrategy = strategy_data["strategy"].get("type", "DEFAULT")

        print "=== [EVENT] City Built: %s | Strategy Assigned: %s ===" % (cityName, szStrategy)

        # Send event to API via HttpRequestManager
        if self.http_mgr:
            return self.http_mgr.post_event("onCityBuilt", argsList, extra_data=strategy_data)

        return False
