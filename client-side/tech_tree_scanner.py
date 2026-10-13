# tech_tree_scanner.py
# Python 2.4 & Python 3 Universal Compatible Tech Tree Scanner for Civilization IV

import sys
from CvPythonExtensions import CyGlobalContext
import http_request_manager

gc = CyGlobalContext()


class TechTreeScanner(object):
    """
    Scans and categorizes the Tech Tree for the active human player (or specified player)
    into known_techs, available_techs, and locked_techs.
    Posts JSON telemetry to http://localhost:8000/api via HttpRequestManager.
    Strict Python 2.4 compatibility - NO ternary operators used.
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

    def scanPlayerTechTree(self, pPlayer=None):
        """
        Scans the player's tech tree options and returns a structured dictionary
        matching the server-side TechTreeScanPayload schema.
        """
        if pPlayer is None:
            pPlayer = gc.getActivePlayer()

        if not pPlayer or pPlayer.isNone():
            return None

        # Ensure player is valid human player
        if not pPlayer.isHuman():
            return None

        iPlayerID = pPlayer.getID()
        iTeamID = pPlayer.getTeam()
        pTeam = gc.getTeam(iTeamID)

        if not pTeam or pTeam.isNone():
            return None

        # Civilization short description
        szCiv = "Unknown"
        if hasattr(pPlayer, 'getCivilizationShortDescription'):
            try:
                szCiv = pPlayer.getCivilizationShortDescription(0)
            except Exception:
                szCiv = "Unknown"

        # Current active research tech ID (-1 if none selected)
        iCurrentResearch = -1
        if hasattr(pPlayer, 'getCurrentResearch'):
            try:
                iCurrentResearch = pPlayer.getCurrentResearch()
            except Exception:
                iCurrentResearch = -1

        known_techs = []
        available_techs = []
        locked_techs = []

        iNumTechs = gc.getNumTechInfos()

        for iTech in range(iNumTechs):
            techInfo = gc.getTechInfo(iTech)
            if not techInfo:
                continue

            szType = ""
            if hasattr(techInfo, 'getType'):
                szType = techInfo.getType()

            szName = ""
            if hasattr(techInfo, 'getDescription'):
                szName = techInfo.getDescription()

            iCost = 0
            if hasattr(techInfo, 'getResearchCost'):
                iCost = techInfo.getResearchCost()

            iGridX = 0
            if hasattr(techInfo, 'getGridX'):
                iGridX = techInfo.getGridX()

            iGridY = 0
            if hasattr(techInfo, 'getGridY'):
                iGridY = techInfo.getGridY()

            iEra = -1
            if hasattr(techInfo, 'getEra'):
                iEra = techInfo.getEra()

            tech_entry = {
                "id": iTech,
                "type": szType,
                "name": szName,
                "cost": iCost,
                "grid_x": iGridX,
                "grid_y": iGridY,
                "era": iEra
            }

            # 1. Check if team already possesses this technology
            if pTeam.isHasTech(iTech):
                tech_entry["status"] = "KNOWN"
                tech_entry["beakers_left"] = 0
                known_techs.append(tech_entry)

            # 2. Check if currently available for research (prerequisites met)
            elif pPlayer.canResearch(iTech, False):
                tech_entry["status"] = "AVAILABLE"
                iBeakersLeft = iCost
                if hasattr(pTeam, 'getResearchLeft'):
                    try:
                        iBeakersLeft = pTeam.getResearchLeft(iTech)
                    except Exception:
                        iBeakersLeft = iCost
                tech_entry["beakers_left"] = iBeakersLeft
                available_techs.append(tech_entry)

            # 3. Check if valid tech in civ's tree, but prerequisites missing
            elif pPlayer.canEverResearch(iTech):
                tech_entry["status"] = "LOCKED"
                tech_entry["beakers_left"] = iCost
                locked_techs.append(tech_entry)

        payload = {
            "event": "onTechTreeScan",
            "player_id": iPlayerID,
            "civilization": szCiv,
            "current_research": iCurrentResearch,
            "known_count": len(known_techs),
            "available_count": len(available_techs),
            "locked_count": len(locked_techs),
            "known_techs": known_techs,
            "available_techs": available_techs,
            "locked_techs": locked_techs
        }

        return payload

    def send_telemetry(self, payload):
        """Sends the JSON tech tree payload to http://localhost:8000/api via HttpRequestManager."""
        if not payload or not self.http_mgr:
            return False

        return self.http_mgr.send_post(payload)

    def run_tech_scan(self, pPlayer=None):
        """
        Main execution entry point to be called on Turn 1 / Game Start / Turn Start.
        """
        payload = self.scanPlayerTechTree(pPlayer)
        if payload:
            return self.send_telemetry(payload)
        return False
