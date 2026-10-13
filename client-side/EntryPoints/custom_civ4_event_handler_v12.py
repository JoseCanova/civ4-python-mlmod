# custom_civ4_event_handler.py
# Production-Ready Custom Event Handler Framework for Civilization IV (Python 2.4 Strict Compatibility)

import sys
import socket

from CvPythonExtensions import CyGlobalContext, YieldTypes
from CvEventManager import CvEventManager
import http_request_manager
import city_buildables_scanner
import tech_tree_scanner
import city_built_handler
import unit_built_handler
import city_do_turn_handler

try:
    import city
    import city_plots
    HAS_CITY_MODULES = True
except ImportError:
    HAS_CITY_MODULES = False

gc = CyGlobalContext()


class CustomCiv4EventHandler(CvEventManager):
    """
    Modular Event Handler Framework for Civilization IV (Python 2.4).
    Delegates network communication to HttpRequestManager to centralize HTTP GET/POST requests,
    allows dynamic registration of event listeners, posts JSON-serialized payloads to /api,
    and provides automated gameplay handlers for cities, combat, construction, and player turns.
    Delegates event behaviors to specialized delegate classes:
      - CityBuiltDelegate (onCityBuilt strategy evaluation)
      - UnitBuiltDelegate (onUnitBuilt strategic role assignment)
      - CityDoTurnDelegate (onCityDoTurn citizen optimization & turn metrics)
    Strict Python 2.4 compatibility - NO ternary operators used in client-side code under any circumstance.
    """

    def __init__(self):
        CvEventManager.__init__(self)

        # Internal registry for dynamic event callbacks: { event_name: [handler_funcs] }
        self._event_listeners = {}

        # Configuration for automated city management
        self.auto_manage_cities = True
        self.city_plot_priority = ("PRODUCTION", "COMMERCE", "FOOD")
        self.city_specialist_priority = [
            "SPECIALIST_SCIENTIST",
            "SPECIALIST_ENGINEER",
            "SPECIALIST_MERCHANT",
            "SPECIALIST_CITIZEN"
        ]
        self.min_food_buffer = 0

        # HTTP Request Manager Instance
        self.server_host = "localhost"
        self.server_port = 8000
        self.api_endpoint = "/api"

        self.http_mgr = http_request_manager.HttpRequestManager(
            host=self.server_host,
            port=self.server_port,
            default_endpoint=self.api_endpoint,
            timeout=2.0
        )

        # Initialize city buildables scanner
        self.buildables_scanner = city_buildables_scanner.CityBuildablesScanner(
            http_mgr=self.http_mgr
        )

        # Initialize tech tree scanner
        self.tech_scanner = tech_tree_scanner.TechTreeScanner(
            http_mgr=self.http_mgr
        )

        # Initialize helper delegate classes
        self.city_built_delegate = city_built_handler.CityBuiltDelegate(
            http_mgr=self.http_mgr
        )

        self.unit_built_delegate = unit_built_handler.UnitBuiltDelegate(
            http_mgr=self.http_mgr
        )

        self.city_do_turn_delegate = city_do_turn_handler.CityDoTurnDelegate(
            http_mgr=self.http_mgr,
            auto_manage_cities=self.auto_manage_cities
        )

        print "CustomCiv4EventHandler: Framework initialized successfully."

    @property
    def server_online(self):
        if self.http_mgr:
            return self.http_mgr.server_online
        return False

    def onEvent(self, argsList):
        return self.handleEvent(argsList)

    def check_http_server(self, host="localhost", port=8000):
        if self.http_mgr:
            self.http_mgr.host = host
            self.http_mgr.port = port
            return self.http_mgr.check_server()
        return False

    def post_event_to_api(self, event_name, argsList):
        if self.http_mgr:
            return self.http_mgr.post_event(event_name, argsList)
        return False

    def register_listener(self, event_name, handler_func):
        if event_name not in self._event_listeners:
            self._event_listeners[event_name] = []
        self._event_listeners[event_name].append(handler_func)

        szFuncName = "custom_callback"
        if hasattr(handler_func, '__name__'):
            szFuncName = handler_func.__name__

        msg = "Registered listener '%s' for event '%s'" % (szFuncName, event_name)
        print msg

    def _dispatch_listeners(self, event_name, argsList):
        if event_name in self._event_listeners:
            for handler in self._event_listeners[event_name]:
                try:
                    handler(argsList)
                except Exception, e:
                    msg = "Error executing listener '%s' for event '%s': %s" % (str(handler), event_name, str(e))
                    print msg

    # ---------------------------------------------------------------------------
    # Event Overloads & Automated Handlers
    # ---------------------------------------------------------------------------

    def onGameStart(self, argsList):
        """Fired when a new game starts (Turn 1). Scans the Tech Tree and initial cities."""
        CvEventManager.onGameStart(self, argsList)

        pPlayer = gc.getActivePlayer()
        if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
            print "=== [EVENT] Game Start (Turn 1): Running Tech Tree Scan ==="
            try:
                self.tech_scanner.run_tech_scan(pPlayer)
            except Exception, e:
                msg = "Warning: Failed running initial Tech Tree scan: %s" % str(e)
                print msg

        self._dispatch_listeners('onGameStart', argsList)

    def onBeginPlayerTurn(self, argsList):
        iGameTurn, iPlayer = argsList
        CvEventManager.onBeginPlayerTurn(self, argsList)

        pPlayer = gc.getPlayer(iPlayer)
        if pPlayer and not pPlayer.isNone():
            if pPlayer.isHuman():
                msg = "=== [EVENT] Turn %d started for Human Player (%s) ===" % (iGameTurn, pPlayer.getCivilizationShortDescription(0))
                print msg
                try:
                    # Run turn buildables scan
                    self.buildables_scanner.run_turn_scan(pPlayer)

                    # Also refresh tech tree options at game start or turn start
                    if iGameTurn == 1 or iGameTurn % 5 == 0:
                        self.tech_scanner.run_tech_scan(pPlayer)
                except Exception, e:
                    msg = "Warning: Failed running turn scan on turn %d: %s" % str(e)
                    print msg
            else:
                msg = "=== [EVENT] Turn %d started for AI Player %d ===" % (iGameTurn, iPlayer)
                print msg

        self._dispatch_listeners('onBeginPlayerTurn', argsList)

    def onCityDoTurn(self, argsList):
        """
        Fired when a city completes turn processing.
        Delegates citizen optimization and turn metric telemetry to CityDoTurnDelegate helper.
        """
        pCity, iPlayer = argsList
        CvEventManager.onCityDoTurn(self, argsList)

        if pCity and not pCity.isNone():
            self.city_do_turn_delegate.handle_city_do_turn(pCity, iPlayer, argsList)

        self._dispatch_listeners('onCityDoTurn', argsList)

    def onCityBuilt(self, argsList):
        """
        Fired when a new city is founded.
        Delegates strategy evaluation and behavior management to CityBuiltDelegate helper class.
        """
        pCity = argsList[0]
        CvEventManager.onCityBuilt(self, argsList)

        if pCity and not pCity.isNone():
            self.city_built_delegate.handle_city_built(pCity, argsList)

        self._dispatch_listeners('onCityBuilt', argsList)

    def onUnitBuilt(self, argsList):
        """
        Fired when a unit completes training in a city.
        Delegates role classification and telemetry reporting to UnitBuiltDelegate helper class.
        """
        pCity, pUnit = argsList
        CvEventManager.onUnitBuilt(self, argsList)

        if pCity and pUnit:
            self.unit_built_delegate.handle_unit_built(pCity, pUnit, argsList)

        self._dispatch_listeners('onUnitBuilt', argsList)

    def onBuildingBuilt(self, argsList):
        pCity, iBuildingType = argsList
        CvEventManager.onBuildingBuilt(self, argsList)

        if pCity:
            szBuildingName = "Unknown Building"
            buildingInfo = gc.getBuildingInfo(iBuildingType)
            if buildingInfo:
                szBuildingName = buildingInfo.getType()

            msg = "=== [EVENT] Building Constructed: %s in %s ===" % (szBuildingName, pCity.getName())
            print msg
            self.post_event_to_api("onBuildingBuilt", argsList)

        self._dispatch_listeners('onBuildingBuilt', argsList)

    def onTechAcquired(self, argsList):
        eTech, eTeam, ePlayer, bAnnounce = argsList
        CvEventManager.onTechAcquired(self, argsList)

        pPlayer = gc.getPlayer(ePlayer)
        techInfo = gc.getTechInfo(eTech)
        szTechName = "Unknown Tech"
        if techInfo:
            szTechName = techInfo.getType()

        msg = "=== [EVENT] Tech Researched: %s by Player %d ===" % (szTechName, ePlayer)
        print msg

        # Post event notification
        self.post_event_to_api("onTechAcquired", argsList)

        # Trigger updated tech tree scan if human player acquired tech
        if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
            try:
                self.tech_scanner.run_tech_scan(pPlayer)
            except Exception, e:
                msg = "Warning: Failed running updated Tech Tree scan: %s" % str(e)
                print msg

        self._dispatch_listeners('onTechAcquired', argsList)
