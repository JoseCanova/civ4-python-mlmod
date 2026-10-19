# unit_built_handler.py
# Python 2.4 Compatible Delegate Handler for Civ IV Unit Built Events

from CvPythonExtensions import CyGlobalContext

gc = CyGlobalContext()


class UnitBuiltDelegate(object):
    """
    Delegate helper class that manages unit role assignment, post-training behavior,
    and telemetry reporting when a unit is trained (onUnitBuilt event).
    Separates event handling from unit classification and tactical role assignment.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self, http_mgr=None):
        self.http_mgr = http_mgr

    def classify_unit_role(self, pUnit):
        """
        Classifies the trained unit into a strategic role based on unit info and domain.
        Uses strict Python 2.4 if/else blocks - NO ternary operators.
        """
        if not pUnit:
            return "UNKNOWN"

        iUnitType = pUnit.getUnitType()
        unitInfo = gc.getUnitInfo(iUnitType)

        if not unitInfo:
            return "GENERAL"

        szType = ""
        if hasattr(unitInfo, 'getType'):
            szType = unitInfo.getType()

        # Settler unit classification
        if "SETTLER" in szType:
            return "EXPANSION_FOUND_CITY"

        # Worker unit classification
        if "WORKER" in szType:
            return "INFRASTRUCTURE_IMPROVE"

        # Scout / Explorer classification
        if "SCOUT" in szType or "EXPLORER" in szType:
            return "RECON_EXPLORE"

        # Check combat strength for military classification
        iCombat = 0
        if hasattr(unitInfo, 'getCombat'):
            iCombat = unitInfo.getCombat()

        # Check domain (LAND, SEA, AIR)
        iDomain = -1
        if hasattr(unitInfo, 'getDomainType'):
            iDomain = unitInfo.getDomainType()

        # Domain 2 = Domain Sea in Civ IV
        if iDomain == 2:
            return "NAVAL_PATROL"

        # Domain 3 = Domain Air in Civ IV
        if iDomain == 3:
            return "AIR_DEFENSE"

        if iCombat > 0:
            if iCombat >= 6:
                return "MILITARY_ASSAULT"
            else:
                return "MILITARY_GARRISON"

        return "SUPPORT"

    def determine_unit_telemetry(self, pCity, pUnit):
        """
        Builds a structured metadata payload describing the trained unit's
        combat strength, domain, experience, and assigned strategic role.
        """
        if not pUnit:
            return None

        role = self.classify_unit_role(pUnit)

        iUnitID = pUnit.getID()
        szUnitName = pUnit.getName()
        iOwner = pUnit.getOwner()
        iUnitType = pUnit.getUnitType()

        iLevel = 1
        if hasattr(pUnit, 'getLevel'):
            iLevel = pUnit.getLevel()

        iExperience = 0
        if hasattr(pUnit, 'getExperience'):
            iExperience = pUnit.getExperience()

        szCityName = "Unknown City"
        if pCity and not pCity.isNone():
            szCityName = pCity.getName()

        unit_payload = {
            "unit_details": {
                "unit_id": iUnitID,
                "unit_name": szUnitName,
                "unit_type_id": iUnitType,
                "owner": iOwner,
                "trained_in_city": szCityName,
                "assigned_role": role,
                "level": iLevel,
                "experience": iExperience
            }
        }

        return unit_payload

    def handle_unit_built(self, pCity, pUnit, argsList):
        """
        Executes the behavior when onUnitBuilt is delegated from CustomCiv4EventHandler.
        Classifies unit role and posts JSON telemetry to the HTTP server.
        """
        if not pUnit:
            return False

        szUnitName = pUnit.getName()
        szCityName = "Unknown City"
        if pCity and not pCity.isNone():
            szCityName = pCity.getName()

        telemetry_data = self.determine_unit_telemetry(pCity, pUnit)

        szRole = "GENERAL"
        if telemetry_data:
            if "unit_details" in telemetry_data:
                szRole = telemetry_data["unit_details"].get("assigned_role", "GENERAL")

        msg = "=== [EVENT] Unit Trained: %s in %s | Strategic Role: %s ===" % (szUnitName, szCityName, szRole)
        print msg

        if self.http_mgr:
            return self.http_mgr.post_event("onUnitBuilt", argsList, extra_data=telemetry_data)

        return False
