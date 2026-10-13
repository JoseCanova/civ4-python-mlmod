# test_map_modules.py
# Reusable Map Inspector Class for Civilization IV (Python 2.4 compatible)

import map_scanner
import map_analyzer

class MapInspector(object):
    """
    Encapsulates MapScanner and MapAnalyzer into a reusable class.
    Instances can be refreshed and run repeatedly during gameplay or from the in-game console (~).
    """
    def __init__(self, pPlayer=None):
        self.pPlayer = pPlayer
        self.scanner = None
        self.refresh()

    def refresh(self):
        """Re-initializes the MapScanner with current player context."""
        self.scanner = map_scanner.MapScanner(self.pPlayer)

    def run(self):
        """
        Executes a fresh scan and prints the map summary and detailed terrain stats.
        Can be called repeatedly at any point during gameplay.
        """
        self.refresh()
        pPlayer = self.scanner.getPlayer()
        if not pPlayer or pPlayer.isNone():
            print "MapInspector Error: Invalid or missing player instance."
            return

        # 1. Map Scanner Summary
        summary = self.scanner.scanMapSummary()
        if not summary:
            print "MapInspector Error: Could not retrieve map summary."
            return

        szHeader = " MAP INSPECTOR REPORT (Player %d, Team %d) " % (
            summary["player_id"], summary["team_id"]
        )
        print "=========================================="
        print szHeader
        print "=========================================="
        print "Map Dimensions  : %dx%d (%d total plots)" % (
            summary["grid_width"], summary["grid_height"], summary["total_plots"]
        )
        print "Revealed Plots  : %d" % summary["revealed_plots_count"]
        print "Visible Plots   : %d" % summary["visible_plots_count"]
        print "------------------------------------------"

        # 2. Map Analyzer Aggregate Statistics
        stats = map_analyzer.summarizeTerrainAndResources(pPlayer)
        if stats:
            print "DOMAINS        : %s" % str(stats["domains"])
            print "RIVER PLOTS    : %d" % stats["river_plots"]
            print "RESOURCES      : %s" % str(stats["bonuses"])
            print "IMPROVEMENTS   : %s" % str(stats["improvements"])
        print "==========================================\n"


def run_scan(pPlayer=None):
    inspector = MapInspector(pPlayer)
    inspector.run()
    return inspector

