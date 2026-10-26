from CvPythonExtensions import *


def classify_building_role(iBuildingType):
    """
    Classifies constructed buildings into strategic categories.
    Python 2.4 strict compatibility (no ternary operators).
    """
    if iBuildingType < 0:
        return "UNKNOWN"

    buildingInfo = gc.getBuildingInfo(iBuildingType)
    if not buildingInfo:
        return "GENERAL"

    szType = ""
    if hasattr(buildingInfo, 'getType'):
        szType = buildingInfo.getType()

    # 1. World and National Wonders
    iClass = buildingInfo.getBuildingClassType()
    if iClass != -1:
        classInfo = gc.getBuildingClassInfo(iClass)
        if classInfo:
            if hasattr(classInfo, 'getMaxGlobalInstances') and classInfo.getMaxGlobalInstances() == 1:
                return "WORLD_WONDER"
            if hasattr(classInfo, 'getMaxPlayerInstances') and classInfo.getMaxPlayerInstances() > 0:
                return "NATIONAL_WONDER"

    # 2. Military Infrastructure
    if hasattr(buildingInfo, 'getFreeExperience') and buildingInfo.getFreeExperience() > 0:
        return "MILITARY_PRODUCTION"
    if hasattr(buildingInfo, 'getDefenseModifier') and buildingInfo.getDefenseModifier() > 0:
        return "DEFENSIVE_FORTIFICATION"

    # 3. Growth & Population Sustainment
    if hasattr(buildingInfo, 'getFoodKept') and buildingInfo.getFoodKept() > 0:
        return "CITY_GROWTH"

    # 4. Built-in Advisor Fallback (Military=0, Economy=1, Religion=2, Science=3, Culture=4, Growth=5)
    if hasattr(buildingInfo, 'getAdvisorType'):
        iAdv = buildingInfo.getAdvisorType()
        if iAdv == 0:
            return "MILITARY"
        elif iAdv == 1:
            return "ECONOMIC"
        elif iAdv == 2:
            return "RELIGIOUS"
        elif iAdv == 3:
            return "SCIENCE"
        elif iAdv == 4:
            return "CULTURE"
        elif iAdv == 5:
            return "GROWTH"

    return "INFRASTRUCTURE"

