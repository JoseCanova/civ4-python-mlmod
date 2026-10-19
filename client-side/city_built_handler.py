# city_built_handler.py
# Python 2.4 Compatible Delegate Handler for Civ IV City Built Events

from CvPythonExtensions import CyGlobalContext

gc = CyGlobalContext()


class CityBuiltDelegate(object):
    """
    Delegate helper class that manages the strategic behavior and telemetry payload
    when a new city is founded (onCityBuilt event).
    Separates event dispatching from gameplay logic and strategy determination.
    Decoupled from networking; returns structured payload dicts for local database buffering.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self):
        pass

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
            "event": "onCityBuilt",
            "city_name": cityName,
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

    def handle_city_built(self, pCity, argsList=None):
        """
        Executes behavior when onCityBuilt is delegated from CustomCiv4EventHandler.
        Calculates city strategy and returns the structured payload dictionary.
        """
        if not pCity or pCity.isNone():
            return None

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

        msg = "=== [EVENT] City Built: %s | Strategy Assigned: %s ===" % (cityName, szStrategy)
        print msg

        return strategy_data
