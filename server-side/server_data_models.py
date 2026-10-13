# server_data_models.py
"""
Server-side Data Models and Parsers for Civilization IV Telemetry Server.
Parses JSON payloads received from Civ IV client modules (HttpRequestManager,
CityBuildablesScanner, CustomCiv4EventHandler, MapScanner).
"""

class CyCityData:
    """Represents a serialized CyCity instance from Civ IV."""
    def __init__(self, name="", owner=-1, population=0, x=-1, y=-1, city_id=-1):
        self.name = name
        self.owner = owner
        self.population = population
        self.x = x
        self.y = y
        self.city_id = city_id

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        return cls(
            name=d.get("name", ""),
            owner=d.get("owner", -1),
            population=d.get("population", 0),
            x=d.get("x", -1),
            y=d.get("y", -1),
            city_id=d.get("id", -1)
        )

    def __repr__(self):
        return "<CyCity '%s' (ID: %d, Owner: %d, Pop: %d, Pos: %d,%d)>" % (
            self.name, self.city_id, self.owner, self.population, self.x, self.y
        )


class CyUnitData:
    """Represents a serialized CyUnit instance from Civ IV."""
    def __init__(self, name="", owner=-1, unit_type=-1, x=-1, y=-1, unit_id=-1):
        self.name = name
        self.owner = owner
        self.unit_type = unit_type
        self.x = x
        self.y = y
        self.unit_id = unit_id

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        return cls(
            name=d.get("name", ""),
            owner=d.get("owner", -1),
            unit_type=d.get("unit_type", -1),
            x=d.get("x", -1),
            y=d.get("y", -1),
            unit_id=d.get("id", -1)
        )

    def __repr__(self):
        return "<CyUnit '%s' (ID: %d, Owner: %d, Type: %d, Pos: %d,%d)>" % (
            self.name, self.unit_id, self.owner, self.unit_type, self.x, self.y
        )


class BuildableItem:
    """Represents a unit or building available for training/construction in a city."""
    def __init__(self, item_type="", cost=0):
        self.item_type = item_type  # XML Type key, e.g. 'UNIT_SETTLER' or 'BUILDING_GRANARY'
        self.cost = cost            # Production hammer cost

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        return cls(
            item_type=d.get("type", ""),
            cost=d.get("cost", 0)
        )

    def __repr__(self):
        return "%s (Cost: %d)" % (self.item_type, self.cost)


class CityBuildablesEntry:
    """Represents buildable units and buildings for a specific city."""
    def __init__(self, city_name="", city_id=-1, available_units=None, available_buildings=None):
        self.city_name = city_name
        self.city_id = city_id
        self.available_units = available_units if available_units is not None else []
        self.available_buildings = available_buildings if available_buildings is not None else []

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        
        raw_units = d.get("available_units", [])
        units = []
        for u in raw_units:
            item = BuildableItem.from_dict(u)
            if item:
                units.append(item)

        raw_buildings = d.get("available_buildings", [])
        buildings = []
        for b in raw_buildings:
            item = BuildableItem.from_dict(b)
            if item:
                buildings.append(item)

        return cls(
            city_name=d.get("name", ""),
            city_id=d.get("id", -1),
            available_units=units,
            available_buildings=buildings
        )

    def __repr__(self):
        return "<City '%s' (ID: %d) -> Units: %d, Buildings: %d>" % (
            self.city_name, self.city_id, len(self.available_units), len(self.available_buildings)
        )


class TurnBuildablesScanPayload:
    """Parses onCityBuildablesScan JSON telemetry posted at turn start."""
    def __init__(self, turn=0, player_id=0, cities_count=0, cities=None):
        self.turn = turn
        self.player_id = player_id
        self.cities_count = cities_count
        self.cities = cities if cities is not None else []

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        
        raw_cities = d.get("cities", [])
        parsed_cities = []
        for c in raw_cities:
            entry = CityBuildablesEntry.from_dict(c)
            if entry:
                parsed_cities.append(entry)

        return cls(
            turn=d.get("turn", 0),
            player_id=d.get("player_id", 0),
            cities_count=d.get("cities_count", len(parsed_cities)),
            cities=parsed_cities
        )

    def summary(self):
        lines = []
        lines.append("=== BUILDABLES SCAN REPORT (Turn %d, Player %d) ===" % (self.turn, self.player_id))
        lines.append("Total Cities Scanned: %d" % len(self.cities))
        for c in self.cities:
            lines.append("  City: %s (ID: %d)" % (c.city_name, c.city_id))
            units_str = ", ".join([repr(u) for u in c.available_units])
            buildings_str = ", ".join([repr(b) for b in c.available_buildings])
            lines.append("    Units (%d)    : %s" % (len(c.available_units), units_str if units_str else "None"))
            lines.append("    Buildings (%d): %s" % (len(c.available_buildings), buildings_str if buildings_str else "None"))
        lines.append("==================================================")
        return "\n".join(lines)


class GenericEventPayload:
    """Parses standard game event payloads posted by CustomCiv4EventHandler."""
    def __init__(self, event_name="", args=None, extra_data=None):
        self.event_name = event_name
        self.args = args if args is not None else []
        self.extra_data = extra_data if extra_data is not None else {}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        
        event_name = d.get("event", "UNKNOWN_EVENT")
        raw_args = d.get("args", [])
        
        parsed_args = []
        for arg in raw_args:
            if isinstance(arg, dict) and "_type" in arg:
                obj_type = arg.get("_type")
                if obj_type == "CyCity":
                    parsed_args.append(CyCityData.from_dict(arg))
                elif obj_type == "CyUnit":
                    parsed_args.append(CyUnitData.from_dict(arg))
                else:
                    parsed_args.append(arg)
            else:
                parsed_args.append(arg)

        extra = {}
        for k, v in d.items():
            if k not in ("event", "args"):
                extra[k] = v

        return cls(
            event_name=event_name,
            args=parsed_args,
            extra_data=extra
        )

    def summary(self):
        args_repr = ", ".join([repr(a) for a in self.args])
        extra_repr = (" | Extra: " + str(self.extra_data)) if self.extra_data else ""
        return "[EVENT] %s -> Args: [%s]%s" % (self.event_name, args_repr, extra_repr)


class PayloadDispatcher:
    """Central parser/dispatcher that routes incoming JSON payloads to specific data model classes."""
    @staticmethod
    def parse_payload(json_dict):
        if not isinstance(json_dict, dict):
            return None
        
        event_type = json_dict.get("event", "")
        if event_type == "onCityBuildablesScan":
            return TurnBuildablesScanPayload.from_dict(json_dict)
        else:
            return GenericEventPayload.from_dict(json_dict)
