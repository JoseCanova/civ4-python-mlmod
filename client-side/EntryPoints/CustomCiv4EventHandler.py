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

try:
    import turn_db_facade
    HAS_DB_FACADE = True
except ImportError: 
    HAS_DB_FACADE = False
    
try:
    import simplejson as json
    HAS_JSON = True
except ImportError:
    try:
        import json
        HAS_JSON = True
    except ImportError:
        json = None
        HAS_JSON = False

gc = CyGlobalContext()


class CustomCiv4EventHandler(CvEventManager):
    """
    Modular Event Handler Framework for Civilization IV (Python 2.4).
    Buffers all gameplay event payloads locally into Berkeley DB (turn_db_facade),
    submits a single consolidated turn batch to the HTTP server on onEndPlayerTurn,
    purges processed events from local DB upon successful submission to prevent memory growth in 32-bit mode,
    and closes Berkeley DB handles cleanly on onGameEnd / onOnExit / onExit to release lock files and prevent memory leaks.
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
        self.buildables_scanner = city_buildables_scanner.CityBuildablesScanner()

        # Initialize tech tree scanner
        self.tech_scanner = tech_tree_scanner.TechTreeScanner()

        # Initialize helper delegate classes
        self.city_built_delegate = city_built_handler.CityBuiltDelegate()

        self.unit_built_delegate = unit_built_handler.UnitBuiltDelegate()

        self.city_do_turn_delegate = city_do_turn_handler.CityDoTurnDelegate(
            auto_manage_cities=self.auto_manage_cities
        )

        if HAS_DB_FACADE and HAS_JSON:
            self.db_facade = turn_db_facade.TurnDatabaseFacade("turn_database.db")
        else:
            self.db_facade = None 

        print("CustomCiv4EventHandler: Framework initialized successfully.")

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

    def register_listener(self, event_name, handler_func):
        if event_name not in self._event_listeners:
            self._event_listeners[event_name] = []
        self._event_listeners[event_name].append(handler_func)

        szFuncName = "custom_callback"
        if hasattr(handler_func, '__name__'):
            szFuncName = handler_func.__name__

        msg = "Registered listener '%s' for event '%s'" % (szFuncName, event_name)
        print(msg)

    def _dispatch_listeners(self, event_name, argsList):
        if event_name in self._event_listeners:
            for handler in self._event_listeners[event_name]:
                try:
                    handler(argsList)
                except Exception:
                    e = sys.exc_info()[1]
                    msg = "Error executing listener '%s' for event '%s': %s" % (str(handler), event_name, str(e))
                    print(msg)

    def _save_db(self, payload):
        """
        Buffers event payload into Berkeley DB via TurnDatabaseFacade for the current game turn.
        Stamps turn number onto payload if missing.
        """
        if not payload or not isinstance(payload, dict):
            return False

        iGameTurn = 0
        pGame = gc.getGame()
        if pGame and not pGame.isNone():
            iGameTurn = pGame.getGameTurn()

        if "turn" not in payload:
            payload["turn"] = iGameTurn

        if self.db_facade and hasattr(self.db_facade, 'insert'):
            try:
                self.db_facade.insert(iGameTurn, payload)
                return True
            except Exception:
                e = sys.exc_info()[1]
                msg = "Warning: Failed saving payload to DB for turn %d: %s" % (iGameTurn, str(e))
                print(msg)
        return False

    def close_database(self):
        """
        Safely closes the local Berkeley DB instance to release file locks,
        flush dirty pages to disk, and prevent memory/resource leaks in 32-bit Civ IV mode.
        """
        if self.db_facade and hasattr(self.db_facade, 'close'):
            try:
                self.db_facade.close()
                print("CustomCiv4EventHandler: Closed Berkeley DB connection cleanly.")
            except Exception:
                e = sys.exc_info()[1]
                print("CustomCiv4EventHandler Warning: Error closing Berkeley DB: %s" % str(e))

    # ---------------------------------------------------------------------------
    # Event Overloads & Automated Handlers
    # ---------------------------------------------------------------------------

    def onGameStart(self, argsList):
        """Fired when a new game starts (Turn 1). Scans the Tech Tree and initial cities."""
        CvEventManager.onGameStart(self, argsList)

        try:
            pPlayer = gc.getActivePlayer()
            if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
                payload = self.tech_scanner.scanPlayerTechTree(pPlayer)
                if payload:
                    self._save_db(payload)
        except Exception:
            e = sys.exc_info()[1]
            msg = "Warning: Failed running initial Tech Tree scan: %s" % str(e)
            print(msg)

        self._dispatch_listeners('onGameStart', argsList)

    def onGameEnd(self, argsList):
        """
        Fired when the game ends (Victory or Defeat screen).
        Flushes and closes the Berkeley DB cleanly to prevent lock files or memory leaks.
        """
        if hasattr(CvEventManager, 'onGameEnd'):
            CvEventManager.onGameEnd(self, argsList)

        print("=== [EVENT] Game Ended ===")
        self.close_database()
        self._dispatch_listeners('onGameEnd', argsList)

    def onOnExit(self, argsList):
        """
        Primary Civ IV event fired when exiting to main menu or quitting the game.
        Guarantees database locks are released and resources are freed.
        """
        if hasattr(CvEventManager, 'onOnExit'):
            CvEventManager.onOnExit(self, argsList)

        print("=== [EVENT] Exiting Game Session (onOnExit) ===")
        self.close_database()
        self._dispatch_listeners('onOnExit', argsList)

    def onExit(self, argsList):
        """
        Fallback hook for alternate Civ IV mod configurations using 'onExit'.
        """
        if hasattr(CvEventManager, 'onExit'):
            CvEventManager.onExit(self, argsList)

        print("=== [EVENT] Exiting Game Session (onExit) ===")
        self.close_database()
        self._dispatch_listeners('onExit', argsList)

    def onBeginPlayerTurn(self, argsList):
        iGameTurn, iPlayer = argsList
        CvEventManager.onBeginPlayerTurn(self, argsList)

        pPlayer = gc.getPlayer(iPlayer)
        if pPlayer and not pPlayer.isNone():
            if pPlayer.isHuman():
                msg = "=== [EVENT] Turn %d started for Human Player (%s) ===" % (iGameTurn, pPlayer.getCivilizationShortDescription(0))
                print(msg)
                try:
                    build_payload = self.buildables_scanner.scanActivePlayerCities(pPlayer, True)
                    if build_payload:
                        self._save_db(build_payload)

                    if iGameTurn == 1 or iGameTurn % 5 == 0:
                        tech_payload = self.tech_scanner.scanPlayerTechTree(pPlayer)
                        if tech_payload:
                            self._save_db(tech_payload)
                except Exception:
                    e = sys.exc_info()[1]
                    msg = "Warning: Failed running turn scan on turn %d: %s" % (iGameTurn, str(e))
                    print(msg)
            else:
                msg = "=== [EVENT] Turn %d started for AI Player %d ===" % (iGameTurn, iPlayer)
                print(msg)

        self._dispatch_listeners('onBeginPlayerTurn', argsList)

    def onCityDoTurn(self, argsList):
        pCity, iPlayer = argsList
        CvEventManager.onCityDoTurn(self, argsList)

        if pCity and not pCity.isNone():
            telemetry_data = self.city_do_turn_delegate.handle_city_do_turn(pCity, iPlayer, argsList)
            if telemetry_data:
                self._save_db(telemetry_data)

        self._dispatch_listeners('onCityDoTurn', argsList)

    def onCityBuilt(self, argsList):
        pCity = argsList[0]
        CvEventManager.onCityBuilt(self, argsList)

        if pCity and not pCity.isNone():
            pPlayer = gc.getActivePlayer()
            if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
                strategy_data = self.city_built_delegate.handle_city_built(pCity, argsList)
                if strategy_data:
                    self._save_db(strategy_data)

        self._dispatch_listeners('onCityBuilt', argsList)

    def onUnitBuilt(self, argsList):
        pCity, pUnit = argsList
        CvEventManager.onUnitBuilt(self, argsList)

        if pCity and pUnit:
            unit_payload = self.unit_built_delegate.handle_unit_built(pCity, pUnit, argsList)
            if unit_payload:
                self._save_db(unit_payload)

        self._dispatch_listeners('onUnitBuilt', argsList)

    def onBuildingBuilt(self, argsList):
        pCity, iBuildingType = argsList
        CvEventManager.onBuildingBuilt(self, argsList)

        if pCity:
            szBuildingName = "Unknown Building"
            buildingInfo = gc.getBuildingInfo(iBuildingType)
            if buildingInfo:
                szBuildingName = buildingInfo.getType()

            szCityName = "Unknown City"
            if hasattr(pCity, 'getName'):
                szCityName = pCity.getName()

            msg = "=== [EVENT] Building Constructed: %s in %s ===" % (szBuildingName, szCityName)
            print(msg)

            building_payload = {
                "event": "onBuildingBuilt",
                "city_name": szCityName,
                "building_type_id": iBuildingType,
                "building_name": szBuildingName
            }
            self._save_db(building_payload)

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
        print(msg)

        tech_payload = {
            "event": "onTechAcquired",
            "player_id": ePlayer,
            "tech_id": eTech,
            "tech_name": szTechName
        }
        self._save_db(tech_payload)

        if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
            try:
                tech_scan_payload = self.tech_scanner.scanPlayerTechTree(pPlayer)
                if tech_scan_payload:
                    self._save_db(tech_scan_payload)
            except Exception:
                e = sys.exc_info()[1]
                msg = "Warning: Failed running updated Tech Tree scan: %s" % str(e)
                print(msg)

        self._dispatch_listeners('onTechAcquired', argsList)

    def onEndPlayerTurn(self, argsList):
        iGameTurn, iPlayer = argsList
        CvEventManager.onEndPlayerTurn(self, argsList)

        pPlayer = gc.getPlayer(iPlayer)
        if pPlayer and not pPlayer.isNone() and pPlayer.isHuman():
            if self.db_facade and hasattr(self.db_facade, 'get_turn_records'):
                turn_records = self.db_facade.get_turn_records(iGameTurn)
                if turn_records and len(turn_records) > 0:
                    batch_payload = {
                        "event": "onTurnBatch",
                        "turn": iGameTurn,
                        "player_id": iPlayer,
                        "event_count": len(turn_records),
                        "events": turn_records
                    }
                    msg = "=== [TURN %d END] Submitting batch of %d events to HTTP server ===" % (
                        iGameTurn, len(turn_records)
                    )
                    print(msg)

                    if self.http_mgr:
                        bSubmitted = self.http_mgr.send_post(batch_payload)
                        if bSubmitted:
                            msg_ok = "=== [TURN %d END] HTTP Batch POST successful. Purging local DB turn records ===" % iGameTurn
                            print(msg_ok)
                            if hasattr(self.db_facade, 'delete_turn_records'):
                                self.db_facade.delete_turn_records(iGameTurn)

        self._dispatch_listeners('onEndPlayerTurn', argsList)
