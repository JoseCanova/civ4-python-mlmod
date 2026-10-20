# unit_built_handler.py
# Python 2.4 & Python 3 Universal Compatible Delegate Handler for Civ IV Unit Built Events

import sys
from CvPythonExtensions import CyGlobalContext

try:
    from CvPythonExtensions import DomainTypes
    HAS_DOMAIN_TYPES = True
except ImportError:
    HAS_DOMAIN_TYPES = False

gc = CyGlobalContext()


class UnitBuiltDelegate(object):
    """
    Delegate helper class that manages unit role assignment, veteran classification,
    and detailed domain model telemetry construction when a unit is trained (onUnitBuilt event).
    Captures unit ID, map coordinates (X, Y), domain type, combat stats, and active promotions.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self):
        pass

    def is_veteran_unit(self, pUnit):
        """
        Determines if a unit qualifies for veteran status based on level (>=3) or XP (>=5).
        """
        if not pUnit:
            return False

        iLevel = 1
        if hasattr(pUnit, 'getLevel'):
            try:
                iLevel = pUnit.getLevel()
            except Exception:
                iLevel = 1

        iExperience = 0
        if hasattr(pUnit, 'getExperience'):
            try:
                iExperience = pUnit.getExperience()
            except Exception:
                iExperience = 0

        if iLevel >= 3 or iExperience >= 5:
            return True

        return False

    def get_unit_promotions(self, pUnit):
        """
        Scans all promotion infos in CyGlobalContext and returns a list of active promotion XML types.
        """
        promotions = []
        if not pUnit:
            return promotions

        if hasattr(gc, 'getNumPromotionInfos'):
            try:
                iNumPromotions = gc.getNumPromotionInfos()
                for iProm in range(iNumPromotions):
                    if hasattr(pUnit, 'isHasPromotion') and pUnit.isHasPromotion(iProm):
                        promInfo = gc.getPromotionInfo(iProm)
                        if promInfo and hasattr(promInfo, 'getType'):
                            promotions.append(promInfo.getType())
            except Exception:
                pass

        return promotions

    def classify_unit_role(self, pUnit):
        """
        Classifies the trained unit into a strategic role based on unit info, domain, combat, and XP level.
        Flags veteran assault units with high XP/Level as VETERAN_ASSAULT.
        Uses DomainTypes enum from CvPythonExtensions if available.
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

        # 1. Non-combat special role unit classification
        if "SETTLER" in szType:
            return "EXPANSION_FOUND_CITY"

        if "WORKER" in szType:
            return "INFRASTRUCTURE_IMPROVE"

        if "SCOUT" in szType or "EXPLORER" in szType:
            return "RECON_EXPLORE"

        # Check domain (LAND, SEA, AIR)
        iDomain = -1
        if hasattr(unitInfo, 'getDomainType'):
            iDomain = unitInfo.getDomainType()

        # Retrieve DomainTypes enum values or defaults (DOMAIN_SEA = 0, DOMAIN_LAND = 1, DOMAIN_AIR = 3)
        iDomainSea = 0
        iDomainAir = 3
        if HAS_DOMAIN_TYPES:
            if hasattr(DomainTypes, 'DOMAIN_SEA'):
                iDomainSea = DomainTypes.DOMAIN_SEA
            if hasattr(DomainTypes, 'DOMAIN_AIR'):
                iDomainAir = DomainTypes.DOMAIN_AIR

        bVeteran = self.is_veteran_unit(pUnit)

        # 2. Check Sea units domain (DOMAIN_SEA = 0)
        if iDomain == iDomainSea:
            if "TRANSPORT" in szType or "GALLEY" in szType or "CARAVEL" in szType or "GALLEON" in szType:
                return "NAVAL_TRANSPORT"
            if bVeteran:
                return "VETERAN_NAVAL_PATROL"
            return "NAVAL_PATROL"

        # 3. Check Air units domain (DOMAIN_AIR = 3)
        if iDomain == iDomainAir:
            if bVeteran:
                return "VETERAN_AIR_DEFENSE"
            return "AIR_DEFENSE"

        # 4. Land Combat units classification
        iCombat = 0
        if hasattr(unitInfo, 'getCombat'):
            iCombat = unitInfo.getCombat()

        if iCombat > 0:
            if iCombat >= 6 or (bVeteran and iCombat >= 4):
                if bVeteran:
                    return "VETERAN_ASSAULT"
                else:
                    return "MILITARY_ASSAULT"
            else:
                if bVeteran:
                    return "VETERAN_GARRISON"
                else:
                    return "MILITARY_GARRISON"

        return "SUPPORT"

    def determine_unit_telemetry(self, pCity, pUnit):
        """
        Builds a structured metadata payload describing the trained unit's
        ID, map position (X, Y), combat strength, domain, HP, promotions, level, and assigned role.
        Includes top-level city_name, unit_id, and map coordinates for direct discrimination.
        """
        if not pUnit:
            return None

        role = self.classify_unit_role(pUnit)

        iUnitID = pUnit.getID()
        szUnitName = pUnit.getName()
        iOwner = pUnit.getOwner()
        iUnitType = pUnit.getUnitType()

        # Map Coordinates
        iX = -1
        iY = -1
        if hasattr(pUnit, 'getX'):
            try:
                iX = pUnit.getX()
            except Exception:
                iX = -1
        if hasattr(pUnit, 'getY'):
            try:
                iY = pUnit.getY()
            except Exception:
                iY = -1

        # Level & Experience
        iLevel = 1
        if hasattr(pUnit, 'getLevel'):
            try:
                iLevel = pUnit.getLevel()
            except Exception:
                iLevel = 1

        iExperience = 0
        if hasattr(pUnit, 'getExperience'):
            try:
                iExperience = pUnit.getExperience()
            except Exception:
                iExperience = 0

        # Domain & Combat Stats
        unitInfo = gc.getUnitInfo(iUnitType)
        iDomain = -1
        szDomainType = "DOMAIN_LAND"
        iBaseCombat = 0

        if unitInfo:
            if hasattr(unitInfo, 'getDomainType'):
                iDomain = unitInfo.getDomainType()
                if iDomain == 0:
                    szDomainType = "DOMAIN_SEA"
                elif iDomain == 1:
                    szDomainType = "DOMAIN_LAND"
                elif iDomain == 2:
                    szDomainType = "DOMAIN_IMMOBILE"
                elif iDomain == 3:
                    szDomainType = "DOMAIN_AIR"

            if hasattr(unitInfo, 'getCombat'):
                iBaseCombat = unitInfo.getCombat()

        # Hit Points & Moves
        iMaxHP = 100
        if hasattr(pUnit, 'maxHitPoints'):
            try:
                iMaxHP = pUnit.maxHitPoints()
            except Exception:
                iMaxHP = 100

        iHP = 100
        if hasattr(pUnit, 'getHP'):
            try:
                iHP = pUnit.getHP()
            except Exception:
                iHP = 100

        iMoves = 1
        if hasattr(pUnit, 'baseMoves'):
            try:
                iMoves = pUnit.baseMoves()
            except Exception:
                iMoves = 1

        promotions_list = self.get_unit_promotions(pUnit)

        szCityName = "Unknown City"
        if pCity and not pCity.isNone():
            szCityName = pCity.getName()

        unit_payload = {
            "event": "onUnitBuilt",
            "city_name": szCityName,
            "unit_id": iUnitID,
            "x": iX,
            "y": iY,
            "unit_details": {
                "unit_id": iUnitID,
                "unit_name": szUnitName,
                "unit_type_id": iUnitType,
                "owner": iOwner,
                "trained_in_city": szCityName,
                "assigned_role": role,
                "level": iLevel,
                "experience": iExperience,
                "x": iX,
                "y": iY,
                "domain_id": iDomain,
                "domain_type": szDomainType,
                "base_combat": iBaseCombat,
                "max_hp": iMaxHP,
                "current_hp": iHP,
                "moves": iMoves,
                "promotions": promotions_list
            }
        }

        return unit_payload

    def handle_unit_built(self, pCity, pUnit, argsList=None):
        """
        Executes behavior when onUnitBuilt is delegated from CustomCiv4EventHandler.
        Classifies unit role and returns the structured telemetry dictionary.
        """
        if not pUnit:
            return None

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
        print(msg)

        return telemetry_data
