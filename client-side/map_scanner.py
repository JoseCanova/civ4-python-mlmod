# map_scanner.py
# Python 2.4 compatible Map Scanner for Civilization IV

from CvPythonExtensions import CyGlobalContext

gc = CyGlobalContext()

class MapScanner(object):
    """
    Scans the map from the perspective of a given player or the active player,
    extracting revealed and currently visible plots.
    """
    def __init__(self, pPlayer=None):
        if pPlayer is None:
            self.pPlayer = gc.getActivePlayer()
        else:
            self.pPlayer = pPlayer

    def getPlayer(self):
        return self.pPlayer

    def getTeam(self):
        if self.pPlayer and not self.pPlayer.isNone():
            return self.pPlayer.getTeam()
        return -1

    def scanMapSummary(self):
        """
        Scans the map grid and returns summary counts of revealed vs visible plots.
        """
        if not self.pPlayer or self.pPlayer.isNone():
            return None

        iTeam = self.getTeam()
        pMap = gc.getMap()

        iWidth = pMap.getGridWidth()
        iHeight = pMap.getGridHeight()
        iTotalPlots = pMap.numPlots()

        iRevealedCount = 0
        iVisibleCount = 0

        for iIndex in range(iTotalPlots):
            pPlot = pMap.plotByIndex(iIndex)
            if pPlot and not pPlot.isNone():
                if pPlot.isRevealed(iTeam, False):
                    iRevealedCount += 1
                    if pPlot.isVisible(iTeam, False):
                        iVisibleCount += 1

        return {
            "player_id": self.pPlayer.getID(),
            "team_id": iTeam,
            "grid_width": iWidth,
            "grid_height": iHeight,
            "total_plots": iTotalPlots,
            "revealed_plots_count": iRevealedCount,
            "visible_plots_count": iVisibleCount
        }

    def getRevealedPlots(self):
        """
        Returns a list of all CyPlot objects revealed to the player's team.
        """
        if not self.pPlayer or self.pPlayer.isNone():
            return []

        iTeam = self.getTeam()
        pMap = gc.getMap()
        iTotalPlots = pMap.numPlots()

        revealed_plots = []
        for iIndex in range(iTotalPlots):
            pPlot = pMap.plotByIndex(iIndex)
            if pPlot and not pPlot.isNone():
                if pPlot.isRevealed(iTeam, False):
                    revealed_plots.append(pPlot)

        return revealed_plots

    def getVisiblePlots(self):
        """
        Returns a list of all CyPlot objects currently in active line-of-sight.
        """
        if not self.pPlayer or self.pPlayer.isNone():
            return []

        iTeam = self.getTeam()
        pMap = gc.getMap()
        iTotalPlots = pMap.numPlots()

        visible_plots = []
        for iIndex in range(iTotalPlots):
            pPlot = pMap.plotByIndex(iIndex)
            if pPlot and not pPlot.isNone():
                if pPlot.isVisible(iTeam, False):
                    visible_plots.append(pPlot)

        return visible_plots
