# server_data_models.py
"""
Server-side Data Models and Parsers for Civilization IV Telemetry Server.
Parses JSON payloads received from Civ IV client modules (HttpRequestManager,
CityBuildablesScanner, CustomCiv4EventHandler, MapScanner, TechTreeScanner,
CityBuiltDelegate, UnitBuiltDelegate, CityDoTurnDelegate).
Supports single-event parsing and consolidated onTurnBatch ingestion with SQLite persistence.
Includes population, happiness, health, and growth metrics tracking for city growth bottlenecks,
as well as unit map positions (X, Y), unique unit IDs, combat domains, and promotion tracking.
"""

import sqlite3
import json


class CyCityData(object):
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
            name=d.get("name", d.get("city_name", "")),
            owner=d.get("owner", -1),
            population=d.get("population", 0),
            x=d.get("x", -1),
            y=d.get("y", -1),
            city_id=d.get("id", d.get("city_id", -1))
        )

    def __repr__(self):
        if self.city_id != -1 and (self.x != -1 or self.y != -1):
            return "<CyCity '%s' (ID: %d, Owner: %d, Pop: %d, Pos: %d,%d)>" % (
                self.name, self.city_id, self.owner, self.population, self.x, self.y
            )
        elif self.city_id != -1:
            return "<CyCity '%s' (ID: %d)>" % (self.name, self.city_id)
        else:
            return self.name if self.name else "Unknown City"


class CyUnitData(object):
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
            name=d.get("name", d.get("unit_name", "")),
            owner=d.get("owner", -1),
            unit_type=d.get("unit_type", d.get("unit_type_id", -1)),
            x=d.get("x", -1),
            y=d.get("y", -1),
            unit_id=d.get("id", d.get("unit_id", -1))
        )

    def __repr__(self):
        if self.unit_id != -1 and (self.x != -1 or self.y != -1):
            return "<CyUnit '%s' (ID: %d, Owner: %d, Type: %d, Pos: %d,%d)>" % (
                self.name, self.unit_id, self.owner, self.unit_type, self.x, self.y
            )
        elif self.unit_id != -1:
            return "<CyUnit '%s' (ID: %d)>" % (self.name, self.unit_id)
        else:
            return self.name if self.name else "Unknown Unit"


class BuildableItem(object):
    """Represents a unit or building available for training/construction in a city."""
    def __init__(self, item_type="", cost=0):
        self.item_type = item_type
        self.cost = cost

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


class CityBuildablesEntry(object):
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
            city_name=d.get("name", d.get("city_name", "")),
            city_id=d.get("id", d.get("city_id", -1)),
            available_units=units,
            available_buildings=buildings
        )

    def __repr__(self):
        return "<City '%s' (ID: %d) -> Units: %d, Buildings: %d>" % (
            self.city_name, self.city_id, len(self.available_units), len(self.available_buildings)
        )


class TurnBuildablesScanPayload(object):
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


class TechItem(object):
    """Represents an individual Technology item in the Civ IV Tech Tree."""
    def __init__(self, tech_id=-1, tech_type="", name="", cost=0, status="", grid_x=0, grid_y=0, era=-1, beakers_left=0):
        self.tech_id = tech_id
        self.tech_type = tech_type
        self.name = name
        self.cost = cost
        self.status = status
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.era = era
        self.beakers_left = beakers_left

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        return cls(
            tech_id=d.get("id", -1),
            tech_type=d.get("type", ""),
            name=d.get("name", ""),
            cost=d.get("cost", 0),
            status=d.get("status", "UNKNOWN"),
            grid_x=d.get("grid_x", 0),
            grid_y=d.get("grid_y", 0),
            era=d.get("era", -1),
            beakers_left=d.get("beakers_left", 0)
        )

    def __repr__(self):
        if self.status == "AVAILABLE" and self.beakers_left > 0:
            return "%s (Cost: %d, Left: %d)" % (self.tech_type, self.cost, self.beakers_left)
        return "%s (Cost: %d)" % (self.tech_type, self.cost)


class TechTreeScanPayload(object):
    """
    Parses onTechTreeScan JSON telemetry posted at game or turn start.
    Contains three distinct lists representing known_techs, available_techs, and locked_techs.
    """
    def __init__(self, player_id=0, civilization="", current_research=-1, 
                 known_count=0, available_count=0, locked_count=0,
                 known_techs=None, available_techs=None, locked_techs=None):
        self.player_id = player_id
        self.civilization = civilization
        self.current_research = current_research
        self.known_count = known_count
        self.available_count = available_count
        self.locked_count = locked_count
        self.known_techs = known_techs if known_techs is not None else []
        self.available_techs = available_techs if available_techs is not None else []
        self.locked_techs = locked_techs if locked_techs is not None else []

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None

        raw_known = d.get("known_techs", [])
        known = [TechItem.from_dict(t) for t in raw_known if t]

        raw_avail = d.get("available_techs", [])
        avail = [TechItem.from_dict(t) for t in raw_avail if t]

        raw_locked = d.get("locked_techs", [])
        locked = [TechItem.from_dict(t) for t in raw_locked if t]

        return cls(
            player_id=d.get("player_id", 0),
            civilization=d.get("civilization", ""),
            current_research=d.get("current_research", -1),
            known_count=d.get("known_count", len(known)),
            available_count=d.get("available_count", len(avail)),
            locked_count=d.get("locked_count", len(locked)),
            known_techs=known,
            available_techs=avail,
            locked_techs=locked
        )

    def summary(self):
        lines = []
        lines.append("=== TECH TREE SCAN REPORT (Player %d - %s) ===" % (self.player_id, self.civilization))
        lines.append("Current Research ID : %s" % str(self.current_research))
        lines.append("Known Techs (%d)    : %s" % (
            len(self.known_techs),
            ", ".join([t.tech_type for t in self.known_techs]) if self.known_techs else "None"
        ))
        lines.append("Available Techs (%d): %s" % (
            len(self.available_techs),
            ", ".join([repr(t) for t in self.available_techs]) if self.available_techs else "None"
        ))
        lines.append("Locked Techs (%d)   : %d technologies remaining in Tech Tree" % (
            len(self.locked_techs), len(self.locked_techs)
        ))
        lines.append("==================================================")
        return "\n".join(lines)


class CityStrategyData(object):
    """Parses strategy configuration assigned to a city upon creation."""
    def __init__(self, strategy_type="DEFAULT", yield_priority=None, specialist_priority=None,
                 recommended_first_build="", min_food_buffer=2, auto_manage_citizens=True):
        self.strategy_type = strategy_type
        self.yield_priority = yield_priority if yield_priority is not None else []
        self.specialist_priority = specialist_priority if specialist_priority is not None else []
        self.recommended_first_build = recommended_first_build
        self.min_food_buffer = min_food_buffer
        self.auto_manage_citizens = auto_manage_citizens

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return cls()
        return cls(
            strategy_type=d.get("type", "DEFAULT"),
            yield_priority=d.get("yield_priority", []),
            specialist_priority=d.get("specialist_priority", []),
            recommended_first_build=d.get("recommended_first_build", ""),
            min_food_buffer=d.get("min_food_buffer", 2),
            auto_manage_citizens=d.get("auto_manage_citizens", True)
        )

    def __repr__(self):
        return "<Strategy '%s' | Yields: %s | Specialists: %s | FirstBuild: %s>" % (
            self.strategy_type,
            str(self.yield_priority),
            str(self.specialist_priority),
            str(self.recommended_first_build)
        )


class CityBuiltPayload(object):
    """Dedicated server payload parser for onCityBuilt events."""
    def __init__(self, city_data=None, strategy_data=None):
        self.city_data = city_data
        self.strategy_data = strategy_data

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None

        city_obj = None
        raw_args = d.get("args", [])
        if raw_args and len(raw_args) > 0 and isinstance(raw_args[0], dict):
            city_obj = CyCityData.from_dict(raw_args[0])
        elif "city_name" in d:
            city_obj = CyCityData(name=d.get("city_name", ""))

        raw_strategy = d.get("strategy", {})
        strategy_obj = CityStrategyData.from_dict(raw_strategy)

        return cls(city_data=city_obj, strategy_data=strategy_obj)

    def summary(self):
        szCity = "Unknown City"
        if self.city_data and self.city_data.name:
            szCity = repr(self.city_data)
        szStrat = repr(self.strategy_data) if self.strategy_data else "No Strategy"
        return "[EVENT] onCityBuilt -> City: %s | %s" % (szCity, szStrat)


class UnitDetailsData(object):
    """Parses unit operational details, positions, domains, and promotions sent during onUnitBuilt events."""
    def __init__(self, unit_id=-1, unit_name="", unit_type_id=-1, owner=-1,
                 trained_in_city="", assigned_role="GENERAL", level=1, experience=0,
                 x=-1, y=-1, domain_id=-1, domain_type="DOMAIN_LAND", base_combat=0,
                 max_hp=100, current_hp=100, moves=1, promotions=None):
        self.unit_id = unit_id
        self.unit_name = unit_name
        self.unit_type_id = unit_type_id
        self.owner = owner
        self.trained_in_city = trained_in_city
        self.assigned_role = assigned_role
        self.level = level
        self.experience = experience
        self.x = x
        self.y = y
        self.domain_id = domain_id
        self.domain_type = domain_type
        self.base_combat = base_combat
        self.max_hp = max_hp
        self.current_hp = current_hp
        self.moves = moves
        self.promotions = promotions if promotions is not None else []

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return cls()
        return cls(
            unit_id=d.get("unit_id", -1),
            unit_name=d.get("unit_name", ""),
            unit_type_id=d.get("unit_type_id", -1),
            owner=d.get("owner", -1),
            trained_in_city=d.get("trained_in_city", ""),
            assigned_role=d.get("assigned_role", "GENERAL"),
            level=d.get("level", 1),
            experience=d.get("experience", 0),
            x=d.get("x", -1),
            y=d.get("y", -1),
            domain_id=d.get("domain_id", -1),
            domain_type=d.get("domain_type", "DOMAIN_LAND"),
            base_combat=d.get("base_combat", 0),
            max_hp=d.get("max_hp", 100),
            current_hp=d.get("current_hp", 100),
            moves=d.get("moves", 1),
            promotions=d.get("promotions", [])
        )

    def __repr__(self):
        pos_str = ""
        if self.x != -1 or self.y != -1:
            pos_str = " @ (%d,%d)" % (self.x, self.y)

        prom_str = ""
        if self.promotions and len(self.promotions) > 0:
            prom_str = " | Promos: " + ", ".join(self.promotions)

        return "<UnitDetails ID:%d '%s' (Role: %s) in %s%s | Combat:%d, Lvl:%d, XP:%d%s>" % (
            self.unit_id, self.unit_name, self.assigned_role, self.trained_in_city, pos_str,
            self.base_combat, self.level, self.experience, prom_str
        )


class UnitBuiltPayload(object):
    """Dedicated server payload parser for onUnitBuilt events."""
    def __init__(self, city_data=None, unit_data=None, unit_details=None):
        self.city_data = city_data
        self.unit_data = unit_data
        self.unit_details = unit_details

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None

        city_obj = None
        unit_obj = None
        raw_args = d.get("args", [])
        if raw_args and len(raw_args) > 0 and isinstance(raw_args[0], dict):
            city_obj = CyCityData.from_dict(raw_args[0])
        elif "city_name" in d:
            city_obj = CyCityData(name=d.get("city_name", ""))

        if raw_args and len(raw_args) > 1 and isinstance(raw_args[1], dict):
            unit_obj = CyUnitData.from_dict(raw_args[1])
        elif "unit_id" in d or "x" in d:
            unit_obj = CyUnitData(
                name=d.get("unit_name", ""),
                unit_id=d.get("unit_id", -1),
                x=d.get("x", -1),
                y=d.get("y", -1)
            )

        raw_details = d.get("unit_details", {})
        details_obj = UnitDetailsData.from_dict(raw_details)

        # Fallback if city_obj is None or has empty name, but details_obj has trained_in_city
        if (not city_obj or not city_obj.name) and details_obj and details_obj.trained_in_city:
            city_obj = CyCityData(name=details_obj.trained_in_city)

        return cls(city_data=city_obj, unit_data=unit_obj, unit_details=details_obj)

    def summary(self):
        szCity = "Unknown City"
        if self.city_data and self.city_data.name:
            szCity = self.city_data.name
        elif self.unit_details and self.unit_details.trained_in_city:
            szCity = self.unit_details.trained_in_city

        szUnit = repr(self.unit_data) if self.unit_data else (
            self.unit_details.unit_name if self.unit_details and self.unit_details.unit_name else "Unknown Unit"
        )
        szDetails = repr(self.unit_details) if self.unit_details else "No Details"
        return "[EVENT] onUnitBuilt in %s -> %s | %s" % (szCity, szUnit, szDetails)


class CityTurnStatusData(object):
    """Parses turn-by-turn yield, project, happiness, and health status for a city during onCityDoTurn events."""
    def __init__(self, city_name="", population=0, food_yield=0, production_yield=0,
                 commerce_yield=0, current_project="", production_turns_left=0,
                 happy_level=0, unhappy_level=0, angry_population=0,
                 good_health=0, bad_health=0, food_turns_left=0):
        self.city_name = city_name
        self.population = population
        self.food_yield = food_yield
        self.production_yield = production_yield
        self.commerce_yield = commerce_yield
        self.current_project = current_project
        self.production_turns_left = production_turns_left
        self.happy_level = happy_level
        self.unhappy_level = unhappy_level
        self.angry_population = angry_population
        self.good_health = good_health
        self.bad_health = bad_health
        self.food_turns_left = food_turns_left

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return cls()
        return cls(
            city_name=d.get("city_name", ""),
            population=d.get("population", 0),
            food_yield=d.get("food_yield", 0),
            production_yield=d.get("production_yield", 0),
            commerce_yield=d.get("commerce_yield", 0),
            current_project=d.get("current_project", ""),
            production_turns_left=d.get("production_turns_left", 0),
            happy_level=d.get("happy_level", 0),
            unhappy_level=d.get("unhappy_level", 0),
            angry_population=d.get("angry_population", 0),
            good_health=d.get("good_health", 0),
            bad_health=d.get("bad_health", 0),
            food_turns_left=d.get("food_turns_left", 0)
        )

    def __repr__(self):
        happy_str = "Happy: %d/%d" % (self.happy_level, self.unhappy_level)
        if self.angry_population > 0:
            happy_str += " (Angry: %d)" % self.angry_population

        health_str = "Health: %d/%d" % (self.good_health, self.bad_health)

        return "<Yields [F:%d, P:%d, C:%d] | Building: %s (%d turns) | Pop: %d | %s | %s>" % (
            self.food_yield, self.production_yield, self.commerce_yield,
            self.current_project, self.production_turns_left,
            self.population, happy_str, health_str
        )


class CityDoTurnPayload(object):
    """Dedicated server payload parser for onCityDoTurn events."""
    def __init__(self, city_data=None, player_id=-1, turn_status=None):
        self.city_data = city_data
        self.player_id = player_id
        self.turn_status = turn_status

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None

        city_obj = None
        player_id = d.get("player_id", -1)
        raw_args = d.get("args", [])
        if raw_args and len(raw_args) > 0 and isinstance(raw_args[0], dict):
            city_obj = CyCityData.from_dict(raw_args[0])
        elif "city_name" in d:
            city_obj = CyCityData(name=d.get("city_name", ""), city_id=d.get("city_id", -1))

        if raw_args and len(raw_args) > 1 and player_id == -1:
            player_id = raw_args[1]

        raw_status = d.get("city_turn_status", {})
        status_obj = CityTurnStatusData.from_dict(raw_status)

        # Fallback if city_obj is None or has empty name, but status_obj has city_name
        if (not city_obj or not city_obj.name) and status_obj and status_obj.city_name:
            if not city_obj:
                city_obj = CyCityData(name=status_obj.city_name)
            else:
                city_obj.name = status_obj.city_name

        return cls(city_data=city_obj, player_id=player_id, turn_status=status_obj)

    def summary(self):
        szCity = "Unknown City"
        if self.city_data and self.city_data.name:
            szCity = self.city_data.name
        elif self.turn_status and self.turn_status.city_name:
            szCity = self.turn_status.city_name

        szStatus = repr(self.turn_status) if self.turn_status else "No Status"
        return "[EVENT] onCityDoTurn -> City: %s | %s" % (szCity, szStatus)


class TurnBatchPayload(object):
    """
    Parses consolidated onTurnBatch JSON payloads submitted by client at turn end.
    Unwraps individual event dictionaries and persists them directly into SQLite tables.
    """
    def __init__(self, turn=0, player_id=0, event_count=0, events=None, parsed_payloads=None):
        self.turn = turn
        self.player_id = player_id
        self.event_count = event_count
        self.raw_events = events if events is not None else []
        self.parsed_payloads = parsed_payloads if parsed_payloads is not None else []

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None

        turn = d.get("turn", 0)
        player_id = d.get("player_id", 0)
        raw_events = d.get("events", [])

        parsed = []
        for evt in raw_events:
            if isinstance(evt, dict):
                # Ensure turn and player_id are stamped
                if "turn" not in evt:
                    evt["turn"] = turn
                if "player_id" not in evt:
                    evt["player_id"] = player_id
                
                parsed_obj = PayloadDispatcher.parse_payload(evt)
                parsed.append((evt, parsed_obj))

        return cls(
            turn=turn,
            player_id=player_id,
            event_count=d.get("event_count", len(raw_events)),
            events=raw_events,
            parsed_payloads=parsed
        )

    def save_to_sqlite(self, db_path="server_telemetry.db"):
        """
        Unwraps and inserts each event in the batch directly into the SQLite database.
        Executes atomically in a single transaction.
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Main event log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_turn_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER,
                player_id INTEGER,
                event_type TEXT,
                payload_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Specialized city strategy events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_strategy_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER,
                player_id INTEGER,
                city_name TEXT,
                strategy_type TEXT,
                recommended_first_build TEXT,
                payload_json TEXT
            )
        """)

        # 3. Specialized unit training table with map coordinates, domain, combat stats, and promotions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_training_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER,
                player_id INTEGER,
                unit_id INTEGER,
                city_name TEXT,
                unit_name TEXT,
                assigned_role TEXT,
                level INTEGER,
                experience INTEGER,
                x INTEGER,
                y INTEGER,
                domain_type TEXT,
                base_combat INTEGER,
                max_hp INTEGER,
                current_hp INTEGER,
                moves INTEGER,
                promotions TEXT,
                payload_json TEXT
            )
        """)

        # 4. Specialized city turn status table (Population, Yields, Happiness, Health, Project)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_do_turn_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER,
                player_id INTEGER,
                city_name TEXT,
                population INTEGER,
                food_yield INTEGER,
                production_yield INTEGER,
                commerce_yield INTEGER,
                current_project TEXT,
                production_turns_left INTEGER,
                happy_level INTEGER,
                unhappy_level INTEGER,
                angry_population INTEGER,
                good_health INTEGER,
                bad_health INTEGER,
                food_turns_left INTEGER,
                payload_json TEXT
            )
        """)

        inserted_count = 0
        for evt_dict, parsed_obj in self.parsed_payloads:
            evt_type = evt_dict.get("event", "UNKNOWN")
            evt_turn = evt_dict.get("turn", self.turn)
            evt_player = evt_dict.get("player_id", self.player_id)
            evt_json = json.dumps(evt_dict)

            # Insert into main event log
            cursor.execute(
                "INSERT INTO server_turn_events (turn, player_id, event_type, payload_json) VALUES (?, ?, ?, ?)",
                (evt_turn, evt_player, evt_type, evt_json)
            )

            # Insert into specialized tables based on event type
            if evt_type == "onCityBuilt":
                strat = evt_dict.get("strategy", {})
                cityName = evt_dict.get("city_name", "Unknown")
                if cityName == "Unknown" and "args" in evt_dict and isinstance(evt_dict["args"], list) and len(evt_dict["args"]) > 0:
                    if isinstance(evt_dict["args"][0], dict):
                        cityName = evt_dict["args"][0].get("name", evt_dict["args"][0].get("city_name", "Unknown"))

                cursor.execute(
                    """INSERT INTO city_strategy_events 
                       (turn, player_id, city_name, strategy_type, recommended_first_build, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (evt_turn, evt_player, cityName, strat.get("type", "DEFAULT"),
                     str(strat.get("recommended_first_build", "")), evt_json)
                )

            elif evt_type == "onUnitBuilt":
                u_details = evt_dict.get("unit_details", {})
                c_name = evt_dict.get("city_name", u_details.get("trained_in_city", "Unknown"))
                
                proms_json = json.dumps(u_details.get("promotions", []))

                cursor.execute(
                    """INSERT INTO unit_training_events
                       (turn, player_id, unit_id, city_name, unit_name, assigned_role, level,
                        experience, x, y, domain_type, base_combat, max_hp, current_hp, moves, promotions, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (evt_turn, evt_player, u_details.get("unit_id", evt_dict.get("unit_id", -1)),
                     c_name, u_details.get("unit_name", "Unknown"), u_details.get("assigned_role", "GENERAL"),
                     u_details.get("level", 1), u_details.get("experience", 0),
                     u_details.get("x", evt_dict.get("x", -1)), u_details.get("y", evt_dict.get("y", -1)),
                     u_details.get("domain_type", "DOMAIN_LAND"), u_details.get("base_combat", 0),
                     u_details.get("max_hp", 100), u_details.get("current_hp", 100),
                     u_details.get("moves", 1), proms_json, evt_json)
                )

            elif evt_type == "onCityDoTurn":
                status = evt_dict.get("city_turn_status", {})
                c_name = evt_dict.get("city_name", status.get("city_name", "Unknown"))
                cursor.execute(
                    """INSERT INTO city_do_turn_events
                       (turn, player_id, city_name, population, food_yield, production_yield,
                        commerce_yield, current_project, production_turns_left, happy_level,
                        unhappy_level, angry_population, good_health, bad_health, food_turns_left, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (evt_turn, evt_player, c_name,
                     status.get("population", 0), status.get("food_yield", 0),
                     status.get("production_yield", 0), status.get("commerce_yield", 0),
                     str(status.get("current_project", "None")), status.get("production_turns_left", 0),
                     status.get("happy_level", 0), status.get("unhappy_level", 0),
                     status.get("angry_population", 0), status.get("good_health", 0),
                     status.get("bad_health", 0), status.get("food_turns_left", 0),
                     evt_json)
                )

            inserted_count += 1

        conn.commit()
        conn.close()
        print("[SQLITE SUCCESS] Saved %d turn events to '%s' for Turn %d (Player %d)." % (
            inserted_count, db_path, self.turn, self.player_id
        ))
        return inserted_count

    def summary(self):
        lines = []
        lines.append("=== TURN BATCH REPORT (Turn %d, Player %d) ===" % (self.turn, self.player_id))
        lines.append("Total Buffered Events in Batch: %d" % len(self.parsed_payloads))
        for idx, (evt_dict, parsed_obj) in enumerate(self.parsed_payloads, 1):
            evt_type = evt_dict.get("event", "UNKNOWN")
            if parsed_obj and hasattr(parsed_obj, 'summary'):
                lines.append("  [%d] %s" % (idx, parsed_obj.summary()))
            else:
                lines.append("  [%d] %s -> %s" % (idx, evt_type, str(evt_dict)))
        lines.append("==============================================")
        return "\n".join(lines)


class GenericEventPayload(object):
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


class PayloadDispatcher(object):
    """Central parser/dispatcher that routes incoming JSON payloads to specific data model classes."""
    @staticmethod
    def parse_payload(json_dict):
        if not isinstance(json_dict, dict):
            return None
        
        event_type = json_dict.get("event", "")
        if event_type == "onTurnBatch":
            return TurnBatchPayload.from_dict(json_dict)
        elif event_type == "onCityBuildablesScan":
            return TurnBuildablesScanPayload.from_dict(json_dict)
        elif event_type == "onTechTreeScan":
            return TechTreeScanPayload.from_dict(json_dict)
        elif event_type == "onCityBuilt":
            return CityBuiltPayload.from_dict(json_dict)
        elif event_type == "onUnitBuilt":
            return UnitBuiltPayload.from_dict(json_dict)
        elif event_type == "onCityDoTurn":
            return CityDoTurnPayload.from_dict(json_dict)
        else:
            return GenericEventPayload.from_dict(json_dict)
