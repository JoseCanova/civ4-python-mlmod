# city_do_turn_handler.py
# Python 2.4 Compatible Delegate Handler for Civ IV City Do Turn Events

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
    Separates event dispatching from citizen optimization and yield calculation.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self, http_mgr=None, auto_manage_cities=True):
        self.http_mgr = http_mgr
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
            except Exception, e:
                msg = "Warning: Failed optimizing citizens for %s: %s" % (pCity.getName(), str(e))
                print msg
                return False

        return False

    def calculate_city_turn_telemetry(self, pCity):
        """
        Calculates turn-level metrics including yield output, growth turns left,
        current production queue item, and food/starvation buffer status.
        Uses strict Python 2.4 if/else blocks - NO ternary operators.
        """
        if not pCity or pCity.isNone():
            return None

        szName = pCity.getName()
        iPop = pCity.getPopulation()

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

        telemetry_payload = {
            "city_turn_status": {
                "city_name": szName,
                "population": iPop,
                "food_yield": iFoodYield,
                "production_yield": iProdYield,
                "commerce_yield": iCommYield,
                "current_project": szCurrentProject,
                "hammers_invested": iHammersInvested,
                "hammers_needed": iHammersNeeded,
                "production_turns_left": iTurnsLeft
            }
        }

        return telemetry_payload

    def handle_city_do_turn(self, pCity, iPlayer, argsList):
        """
        Executes behavior when onCityDoTurn is delegated from CustomCiv4EventHandler.
        Optimizes citizens and posts turn telemetry to HTTP server.
        """
        if not pCity or pCity.isNone():
            return False

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
        print msg

        # Step 3: Post event payload to HTTP server
        if self.http_mgr:
            return self.http_mgr.post_event("onCityDoTurn", argsList, extra_data=telemetry_data)

        return False
