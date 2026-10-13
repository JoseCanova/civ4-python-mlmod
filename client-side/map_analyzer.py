# map_analyzer.py
# Detailed Plot & Terrain Analyzer for Civilization IV (Python 2.4 compatible)

from CvPythonExtensions import CyGlobalContext

gc = CyGlobalContext()

def classifyPlotDomain(pPlot):
    """
    Determines the geographic domain type of a given plot.
    Returns: 'MOUNTAIN', 'HILLS', 'LAKE', 'OCEAN', or 'LAND_FLAT'
    """
    if not pPlot or pPlot.isNone():
        return "UNKNOWN"

    if pPlot.isPeak():
        return "MOUNTAIN"
    elif pPlot.isHills():
        return "HILLS"
    elif pPlot.isWater():
        if pPlot.isLake():
            return "LAKE"
        else:
            return "OCEAN"
    else:
        return "LAND_FLAT"


def getPlotTerrainTag(pPlot):
    """Returns the terrain type string, e.g. 'TERRAIN_GRASS'."""
    if not pPlot or pPlot.isNone():
        return "UNKNOWN"
    
    iTerrain = pPlot.getTerrainType()
    if iTerrain != -1:
        terrainInfo = gc.getTerrainInfo(iTerrain)
        if terrainInfo:
            return terrainInfo.getType()
    return "UNKNOWN"


def getPlotFeatureTag(pPlot):
    """Returns feature type string, e.g. 'FEATURE_FOREST', or 'NONE'."""
    if not pPlot or pPlot.isNone():
        return "NONE"

    iFeature = pPlot.getFeatureType()
    if iFeature != -1:
        featureInfo = gc.getFeatureInfo(iFeature)
        if featureInfo:
            return featureInfo.getType()
    return "NONE"


def getPlotBonusTag(pPlot, iTeam):
    """Returns revealed resource string, e.g. 'BONUS_IRON', or 'NONE'."""
    if not pPlot or pPlot.isNone():
        return "NONE"

    iBonus = pPlot.getBonusType(iTeam)
    if iBonus != -1:
        bonusInfo = gc.getBonusInfo(iBonus)
        if bonusInfo:
            return bonusInfo.getType()
    return "NONE"


def getPlotImprovementTag(pPlot, iTeam):
    """Returns revealed improvement string, e.g. 'IMPROVEMENT_FARM', or 'NONE'."""
    if not pPlot or pPlot.isNone():
        return "NONE"

    iImprovement = pPlot.getRevealedImprovementType(iTeam, False)
    if iImprovement != -1:
        impInfo = gc.getImprovementInfo(iImprovement)
        if impInfo:
            return impInfo.getType()
    return "NONE"


def getPlotRouteTag(pPlot, iTeam):
    """Returns revealed route string, e.g. 'ROUTE_ROAD', or 'NONE'."""
    if not pPlot or pPlot.isNone():
        return "NONE"

    iRoute = pPlot.getRevealedRouteType(iTeam, False)
    if iRoute != -1:
        routeInfo = gc.getRouteInfo(iRoute)
        if routeInfo:
            return routeInfo.getType()
    return "NONE"


def analyzePlot(pPlot, iTeam):
    """
    Extracts detailed terrain, domain, water, river, resource, and improvement info
    for a single plot from a team's perspective.
    """
    if not pPlot or pPlot.isNone():
        return None

    szDomain = classifyPlotDomain(pPlot)
    szTerrain = getPlotTerrainTag(pPlot)
    szFeature = getPlotFeatureTag(pPlot)
    
    bIsRiver = pPlot.isRiver()
    bIsRiverSide = pPlot.isRiverSide()

    szBonus = getPlotBonusTag(pPlot, iTeam)
    szImprovement = getPlotImprovementTag(pPlot, iTeam)
    szRoute = getPlotRouteTag(pPlot, iTeam)

    iRevealedOwner = pPlot.getRevealedOwner(iTeam, False)

    return {
        "x": pPlot.getX(),
        "y": pPlot.getY(),
        "domain": szDomain,           # MOUNTAIN, HILLS, LAKE, OCEAN, LAND_FLAT
        "terrain": szTerrain,         # TERRAIN_GRASS, TERRAIN_PLAINS, etc.
        "feature": szFeature,         # FEATURE_FOREST, FEATURE_JUNGLE, etc.
        "is_river": bIsRiver,
        "is_riverside": bIsRiverSide,
        "bonus": szBonus,             # BONUS_IRON, BONUS_WHEAT, etc.
        "improvement": szImprovement, # IMPROVEMENT_FARM, IMPROVEMENT_MINE, etc.
        "route": szRoute,             # ROUTE_ROAD, ROUTE_RAILROAD, etc.
        "revealed_owner": iRevealedOwner
    }


def analyzeRevealedMap(pPlayer):
    """
    Scans the map and returns a list of detailed plot analysis dictionaries
    for all plots revealed to the player's team.
    """
    if not pPlayer or pPlayer.isNone():
        return []

    iTeam = pPlayer.getTeam()
    pMap = gc.getMap()
    iTotalPlots = pMap.numPlots()

    analyzed_plots = []
    for iIndex in range(iTotalPlots):
        pPlot = pMap.plotByIndex(iIndex)
        if pPlot and not pPlot.isNone():
            if pPlot.isRevealed(iTeam, False):
                data = analyzePlot(pPlot, iTeam)
                if data:
                    analyzed_plots.append(data)

    return analyzed_plots


def summarizeTerrainAndResources(pPlayer):
    """
    Returns aggregate counts of domains, resources, and improvements
    across all revealed plots for the player.
    """
    if not pPlayer or pPlayer.isNone():
        return None

    iTeam = pPlayer.getTeam()
    pMap = gc.getMap()
    iTotalPlots = pMap.numPlots()

    domain_counts = {}
    bonus_counts = {}
    improvement_counts = {}
    river_plot_count = 0

    for iIndex in range(iTotalPlots):
        pPlot = pMap.plotByIndex(iIndex)
        if pPlot and not pPlot.isNone():
            if pPlot.isRevealed(iTeam, False):
                # Domain
                szDomain = classifyPlotDomain(pPlot)
                domain_counts[szDomain] = domain_counts.get(szDomain, 0) + 1

                # River
                if pPlot.isRiver():
                    river_plot_count += 1

                # Bonus
                szBonus = getPlotBonusTag(pPlot, iTeam)
                if szBonus != "NONE":
                    bonus_counts[szBonus] = bonus_counts.get(szBonus, 0) + 1

                # Improvement
                szImprovement = getPlotImprovementTag(pPlot, iTeam)
                if szImprovement != "NONE":
                    improvement_counts[szImprovement] = improvement_counts.get(szImprovement, 0) + 1

    return {
        "player_id": pPlayer.getID(),
        "team_id": iTeam,
        "domains": domain_counts,
        "river_plots": river_plot_count,
        "bonuses": bonus_counts,
        "improvements": improvement_counts
    }
