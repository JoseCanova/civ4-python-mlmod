from CvPythonExtensions import CyGlobalContext, OrderTypes
import city  # Imports cityByName helper function

gc = CyGlobalContext()

def build(cityName, itemDict, bAppend=False, bClearQueue=False):
    """
    Sets or queues production for a city by name.
    
    Usage:
      city.build("Rome", dict(Unit="UNIT_WARRIOR"))
      city.build("Rome", dict(Building="BUILDING_GRANARY"))
      city.build("Rome", dict(Project="PROJECT_MANHATTAN_PROJECT"))
    """
    pCity = city.cityByName(cityName)
    if not pCity or pCity.isNone():
        print "Error: City '%s' not found." % cityName
        return False

    # Clear existing production queue if requested
    if bClearQueue:
        pCity.clearOrderQueue()

    eOrderType = None
    iItemType = -1

    # Identify item category from dictionary keys
    if "Unit" in itemDict or "unit" in itemDict:
        unitKey = itemDict.get("Unit") or itemDict.get("unit")
        eOrderType = OrderTypes.ORDER_TRAIN
        iItemType = gc.getInfoTypeForString(unitKey)

    elif "Building" in itemDict or "building" in itemDict:
        buildingKey = itemDict.get("Building") or itemDict.get("building")
        eOrderType = OrderTypes.ORDER_CONSTRUCT
        iItemType = gc.getInfoTypeForString(buildingKey)

    elif "Project" in itemDict or "project" in itemDict:
        projectKey = itemDict.get("Project") or itemDict.get("project")
        eOrderType = OrderTypes.ORDER_CREATE
        iItemType = gc.getInfoTypeForString(projectKey)

    elif "Process" in itemDict or "process" in itemDict:
        processKey = itemDict.get("Process") or itemDict.get("process")
        eOrderType = OrderTypes.ORDER_MAINTAIN
        iItemType = gc.getInfoTypeForString(processKey)

    # Validate that XML string mapped to a valid integer ID
    if eOrderType is None or iItemType == -1:
        print "Error: Invalid item identifier in dictionary %s" % str(itemDict)
        return False

    # CyCity.pushOrder parameters:
    # (eOrder, iData1, iData2, bSave, bPop, bAppend, bForce)
    pCity.pushOrder(
        eOrderType,  # ORDER_TRAIN, ORDER_CONSTRUCT, etc.
        iItemType,   # XML integer ID of item
        -1,          # iData2 (-1 for default)
        False,       # bSave
        not bAppend, # bPop (If True, replaces current production at top of queue)
        bAppend,     # bAppend (If True, appends to the back of the queue)
        False        # bForce
    )

    print "Set production in %s to %s" % (cityName, str(itemDict))
    return True

