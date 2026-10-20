import json
from typing import Dict, List, Any, Optional

class TechNode:
    """Represents a single technology node in the Python 3 Tech Graph."""
    def __init__(self, data: Dict[str, Any]):
        self.tech_id: int = data.get("id", -1)
        self.tech_type: str = data.get("type", "")
        self.name: str = data.get("name", "")
        self.cost: int = data.get("cost", 0)
        self.grid_x: int = data.get("grid_x", 0)
        self.grid_y: int = data.get("grid_y", 0)
        self.era: int = data.get("era", -1)
        self.status: str = data.get("status", "LOCKED")  # KNOWN, AVAILABLE, LOCKED
        self.beakers_left: int = data.get("beakers_left", self.cost)

    def __repr__(self):
        return f"<Tech {self.tech_type} (x={self.grid_x}, y={self.grid_y}) [{self.status}] Cost:{self.beakers_left}/{self.cost}>"


class Civ4TechTreeBuilder:
    """
    Parses onTechTreeScan JSON telemetry from server_turn_events 
    and constructs a column-indexed DAG for research decisions.
    """
    def __init__(self, scan_payload: Dict[str, Any]):
        self.player_id: int = scan_payload.get("player_id", 0)
        self.civilization: str = scan_payload.get("civilization", "")
        self.current_research: int = scan_payload.get("current_research", -1)
        
        self.nodes: Dict[int, TechNode] = {}
        self.columns: Dict[int, List[TechNode]] = {}
        
        self.known_techs: List[TechNode] = []
        self.available_techs: List[TechNode] = []
        self.locked_techs: List[TechNode] = []

        self._parse_payload(scan_payload)

    def _parse_payload(self, payload: Dict[str, Any]) -> None:
        """Parses known_techs, available_techs, and locked_techs lists."""
        all_raw = (
            payload.get("known_techs", []) + 
            payload.get("available_techs", []) + 
            payload.get("locked_techs", [])
        )

        for raw_item in all_raw:
            node = TechNode(raw_item)
            self.nodes[node.tech_id] = node

            # Organize into status lists
            if node.status == "KNOWN":
                self.known_techs.append(node)
            elif node.status == "AVAILABLE":
                self.available_techs.append(node)
            else:
                self.locked_techs.append(node)

            # Group nodes into grid_x columns (Tiers)
            if node.grid_x not in self.columns:
                self.columns[node.grid_x] = []
            self.columns[node.grid_x].append(node)

    def get_research_frontier(self) -> List[TechNode]:
        """Returns all technologies currently unlocked and ready for research."""
        return sorted(self.available_techs, key=lambda t: (t.beakers_left, t.grid_x))

    def get_column_tier(self, grid_x: int) -> List[TechNode]:
        """Returns all technologies at a specific grid_x column index."""
        return self.columns.get(grid_x, [])

    def find_shortest_cost_tech(self) -> Optional[TechNode]:
        """Finds the AVAILABLE technology with the lowest remaining beaker cost."""
        if not self.available_techs:
            return None
        return min(self.available_techs, key=lambda t: t.beakers_left)

    def find_target_paths_by_grid_y(self, target_grid_y: int) -> List[TechNode]:
        """
        Retrieves all locked/available techs along a specific horizontal branch (grid_y)
        ordered by grid_x depth.
        """
        branch_techs = [
            node for node in self.nodes.values()
            if node.grid_y == target_grid_y and node.status != "KNOWN"
        ]
        return sorted(branch_techs, key=lambda t: t.grid_x)
