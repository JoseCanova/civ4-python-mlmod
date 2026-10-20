# city_do_turn_handler.py
# Python 2.4 & Python 3 Universal Compatible Delegate Handler for Civ IV City Do Turn Events

import sys
from CvPythonExtensions import CyGlobalContext, YieldTypes

gc = CyGlobalContext()

try:
    import city
    HAS_CITY_MODULES = True
except ImportError:
    HAS_CITY_MODULES = False


class CityDoTurnDelegate(object):
    """
    Delegate helper class that manages city citizen optimization and turn telemetry
    when a city processes its turn (onCityDoTurn event).
    Decoupled from networking; returns structured payload dicts for local database buffering.
    Includes population, happiness, health, and growth metrics to track city growth bottlenecks.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self, auto_manage_cities=True):
        self.auto_manage_cities = auto_manage_cities
        self.city_plot_priority = ("PRODUCTION", "COMMERCE", "FOOD")
        self.city_specialist_priority = [
            "SPECIALIST_SCIENTIST",
            "SPECIALIST_ENGINEER",
            "SPECIALIST_MERCHANT",
            "SPECIALIST_CITIZEN"
        ]
        self.min_food_buffer = 0

    def optimize_city_citizens(self, pCity):
        """
        Invokes CityCitizenManager to optimize plot assignments and specialists.
        """
        if not pCity or pCity.isNone():
            return False

        if self.auto_manage_cities and HAS_CITY_MODULES:
            try:
                mgr = city.CityCitizenManager(
                    pCity,
                    priority_yields=self.city_plot_priority,
                    specialist_priority=self.city_specialist_priority,
                    min_food_buffer=self.min_food_buffer
                )
                mgr.optimize()
                return True
            except Exception:
                e = sys.exc_info()[1]
                msg = "Warning: Failed optimizing citizens for %s: %s" % (pCity.getName(), str(e))
                print(msg)
                return False

        return False

    def calculate_city_turn_telemetry(self, pCity):
        """
        Calculates turn-level metrics including yield output, growth turns left,
        current production queue item, food/starvation buffer, and happiness/health statistics.
        Includes top-level city_name and city_id for direct payload identification.
        Uses strict Python 2.4 if/else blocks - NO ternary operators.
        """
        if not pCity or pCity.isNone():
            return None

        szName = pCity.getName()
        iPop = pCity.getPopulation()
        iCityID = -1
        if hasattr(pCity, 'getID'):
            iCityID = pCity.getID()

        iFoodYield = 0
        iProdYield = 0
        iCommYield = 0

        if hasattr(pCity, 'getYieldRate'):
            try:
                iFoodYield = pCity.getYieldRate(YieldTypes.YIELD_FOOD)
                iProdYield = pCity.getYieldRate(YieldTypes.YIELD_PRODUCTION)
                iCommYield = pCity.getYieldRate(YieldTypes.YIELD_COMMERCE)
            except Exception:
                pass

        szCurrentProject = "None"
        if hasattr(pCity, 'getProductionName'):
            try:
                szCurrentProject = pCity.getProductionName()
            except Exception:
                szCurrentProject = "None"

        iTurnsLeft = 0
        if hasattr(pCity, 'getProductionTurnsLeft'):
            try:
                iTurnsLeft = pCity.getProductionTurnsLeft()
            except Exception:
                iTurnsLeft = 0

        iHammersInvested = 0
        if hasattr(pCity, 'getProduction'):
            try:
                iHammersInvested = pCity.getProduction()
            except Exception:
                iHammersInvested = 0

        iHammersNeeded = 0
        if hasattr(pCity, 'getProductionNeeded'):
            try:
                iHammersNeeded = pCity.getProductionNeeded()
            except Exception:
                iHammersNeeded = 0

        # Happiness Metrics
        iHappyLevel = 0
        if hasattr(pCity, 'happyLevel'):
            try:
                iHappyLevel = pCity.happyLevel()
            except Exception:
                iHappyLevel = 0

        iUnhappyLevel = 0
        if hasattr(pCity, 'unhappyLevel'):
            try:
                iUnhappyLevel = pCity.unhappyLevel(0)
            except Exception:
                iUnhappyLevel = 0

        iAngryPop = 0
        if hasattr(pCity, 'angryPopulation'):
            try:
                iAngryPop = pCity.angryPopulation(0)
            except Exception:
                iAngryPop = 0

        # Health Metrics
        iGoodHealth = 0
        if hasattr(pCity, 'goodHealth'):
            try:
                iGoodHealth = pCity.goodHealth()
            except Exception:
                iGoodHealth = 0

        iBadHealth = 0
        if hasattr(pCity, 'badHealth'):
            try:
                iBadHealth = pCity.badHealth(False)
            except Exception:
                iBadHealth = 0

        # Growth Metrics
        iFoodTurnsLeft = 0
        if hasattr(pCity, 'getFoodTurnsLeft'):
            try:
                iFoodTurnsLeft = pCity.getFoodTurnsLeft()
            except Exception:
                iFoodTurnsLeft = 0

        telemetry_payload = {
            "event": "onCityDoTurn",
            "city_name": szName,
            "city_id": iCityID,
            "city_turn_status": {
                "city_name": szName,
                "city_id": iCityID,
                "population": iPop,
                "food_yield": iFoodYield,
                "production_yield": iProdYield,
                "commerce_yield": iCommYield,
                "current_project": szCurrentProject,
                "hammers_invested": iHammersInvested,
                "hammers_needed": iHammersNeeded,
                "production_turns_left": iTurnsLeft,
                "happy_level": iHappyLevel,
                "unhappy_level": iUnhappyLevel,
                "angry_population": iAngryPop,
                "good_health": iGoodHealth,
                "bad_health": iBadHealth,
                "food_turns_left": iFoodTurnsLeft
            }
        }

        return telemetry_payload

    def handle_city_do_turn(self, pCity, iPlayer=0, argsList=None):
        """
        Executes behavior when onCityDoTurn is delegated from CustomCiv4EventHandler.
        Optimizes citizens and returns the turn telemetry payload.
        """
        if not pCity or pCity.isNone():
            return None

        szName = pCity.getName()

        # Step 1: Optimize citizen assignment
        self.optimize_city_citizens(pCity)

        # Step 2: Build telemetry payload
        telemetry_data = self.calculate_city_turn_telemetry(pCity)

        szProject = "None"
        if telemetry_data:
            if "city_turn_status" in telemetry_data:
                szProject = telemetry_data["city_turn_status"].get("current_project", "None")

        msg = "=== [EVENT] City Do Turn: %s | Current Project: %s ===" % (szName, szProject)
        print(msg)

        return telemetry_data
