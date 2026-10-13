# custom_civ4_event_handler.py
# Production-Ready Custom Event Handler Framework for Civilization IV (Python 2.4 Strict Compatibility)

import sys
import socket

from CvPythonExtensions import CyGlobalContext, YieldTypes
from CvEventManager import CvEventManager
import http_request_manager
import city_buildables_scanner
import tech_tree_scanner

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
    Includes automated Turn 1 / Turn Start TechTreeScanner and CityBuildablesScanner.
    Strict Python 2.4 compatibility - NO ternary operators used in client-side code.
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

        print "Registered listener '%s' for event '%s'" % (szFuncName, event_name)

    def _dispatch_listeners(self, event_name, argsList):
        if event_name in self._event_listeners:
            for handler in self._event_listeners[event_name]:
                try:
                    handler(argsList)
                except Exception, e:
                    print "Error executing listener '%s' for event '%s': %s" % (
                        str(handler), event_name, str(e)
                    )

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
                print "Warning: Failed running initial Tech Tree scan: %s" % str(e)

        self._dispatch_listeners('onGameStart', argsList)

    def onBeginPlayerTurn(self, argsList):
        iGameTurn, iPlayer = argsList
        CvEventManager.onBeginPlayerTurn(self, argsList)

        pPlayer = gc.getPlayer(iPlayer)
        if pPlayer and not pPlayer.isNone():
            if pPlayer.isHuman():
                print "=== [EVENT] Turn %d started for Human Player (%s) ===" % (
                    iGameTurn, pPlayer.getCivilizationShortDescription(0)
                )
                try:
                    # Run turn buildables scan
                    self.buildables_scanner.run_turn_scan(pPlayer)

                    # Also refresh tech tree options at game start or turn start
                    if iGameTurn == 1 or iGameTurn % 5 == 0:
                        self.tech_scanner.run_tech_scan(pPlayer)
                except Exception, e:
                    print "Warning: Failed running turn scan on turn %d: %s" % (iGameTurn, str(e))
            else:
                print "=== [EVENT] Turn %d started for AI Player %d ===" % (iGameTurn, iPlayer)

        self._dispatch_listeners('onBeginPlayerTurn', argsList)

    def onCityDoTurn(self, argsList):
        pCity, iPlayer = argsList
        CvEventManager.onCityDoTurn(self, argsList)

        if pCity and not pCity.isNone():
            if self.auto_manage_cities and HAS_CITY_MODULES:
                try:
                    mgr = city.CityCitizenManager(
                        pCity,
                        priority_yields=self.city_plot_priority,
                        specialist_priority=self.city_specialist_priority,
                        min_food_buffer=self.min_food_buffer
                    )
                    mgr.optimize()
                except Exception, e:
                    print "Warning: Failed optimizing citizens for %s: %s" % (pCity.getName(), str(e))

            self.post_event_to_api("onCityDoTurn", argsList)

        self._dispatch_listeners('onCityDoTurn', argsList)

    def onCityBuilt(self, argsList):
        pCity = argsList[0]
        CvEventManager.onCityBuilt(self, argsList)

        if pCity and not pCity.isNone():
            print "=== [EVENT] City Built: %s ===" % pCity.getName()
            self.post_event_to_api("onCityBuilt", argsList)

        self._dispatch_listeners('onCityBuilt', argsList)

    def onUnitBuilt(self, argsList):
        pCity, pUnit = argsList
        CvEventManager.onUnitBuilt(self, argsList)

        if pCity and pUnit:
            print "=== [EVENT] Unit Trained: %s in %s ===" % (pUnit.getName(), pCity.getName())
            self.post_event_to_api("onUnitBuilt", argsList)

        self._dispatch_listeners('onUnitBuilt', argsList)

    def onBuildingBuilt(self, argsList):
        pCity, iBuildingType = argsList
        CvEventManager.onBuildingBuilt(self, argsList)

        if pCity:
            szBuildingName = "Unknown Building"
            buildingInfo = gc.getBuildingInfo(iBuildingType)
            if buildingInfo:
                szBuildingName = buildingInfo.getType()

            print "=== [EVENT] Building Constructed: %s in %s ===" % (szBuildingName, pCity.getName())
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

        print "=== [EVENT] Tech Researched: %s by Player %d ===" % (szTechName, ePlayer)

        # Post event notification
        self.post_event_to_api("onTechAcquired", argsList)

        # Trigger updated tech tree scan if human player acquired tech
        if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
            try:
                self.tech_scanner.run_tech_scan(pPlayer)
            except Exception, e:
                print "Warning: Failed running updated Tech Tree scan: %s" % str(e)

        self._dispatch_listeners('onTechAcquired', argsList)
