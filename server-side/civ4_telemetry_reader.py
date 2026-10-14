#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:23:16 2026

@author: jose
"""

import os
import json
import sqlite3
from typing import Optional, List, Any

# Import v4 models and dispatcher
import server_data_models_v4 as models
from server_data_models_v4 import PayloadDispatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "civ4_telemetry_json.db")

class TelemetryRecord(object):
    """Wrapper holding database metadata alongside the deserialized v4 model instance."""
    def __init__(self, record_id: int, payload_type: str, parsed_model: Any, received_at: str, raw_json: dict) -> None:
        self.record_id = record_id
        self.payload_type = payload_type
        self.parsed_model = parsed_model
        self.received_at = received_at
        self.raw_json = raw_json

    def __repr__(self) -> str:
        model_name = self.parsed_model.__class__.__name__ if self.parsed_model else "None"
        return "<TelemetryRecord ID:%d | Type:'%s' | Model:%s | Date:%s>" % (
            self.record_id, self.payload_type, model_name, self.received_at
        )


class Civ4TelemetryReader(object):
    """
    Handles SQLite database reading and automatic object deserialization into 
    server_data_models_v4 classes based on event type.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _parse_row(self, row: sqlite3.Row) -> TelemetryRecord:
        """Parses a database row into a TelemetryRecord with a deserialized v4 model."""
        record_id = row["id"]
        payload_type = row["payload_type"]
        raw_text = row["json_data"]
        received_at = row["received_at"]

        raw_json = json.loads(raw_text) if raw_text else {}
        parsed_model = PayloadDispatcher.parse_payload(raw_json)

        return TelemetryRecord(
            record_id=record_id,
            payload_type=payload_type,
            parsed_model=parsed_model,
            received_at=received_at,
            raw_json=raw_json
        )

    # --- Generic Readers ---

    def get_record_by_id(self, record_id: int) -> Optional[TelemetryRecord]:
        """Fetches a single telemetry record by primary key ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, payload_type, json_data, received_at FROM telemetry_records WHERE id = ?;",
                (record_id,)
            )
            row = cursor.fetchone()
            return self._parse_row(row) if row else None

    def get_records_by_event_type(self, event_type: str, limit: int = 50) -> List[TelemetryRecord]:
        """Fetches records filtered by payload_type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, payload_type, json_data, received_at 
                FROM telemetry_records 
                WHERE payload_type = ? 
                ORDER BY id DESC LIMIT ?;
            """
            cursor.execute(query, (event_type, limit))
            return [self._parse_row(row) for row in cursor.fetchall()]

    # --- Strongly-Typed Event Specific Readers ---

    def get_buildable_scans(self, player_id: Optional[int] = None, turn: Optional[int] = None, limit: int = 50) -> List[TelemetryRecord]:
        """Reads 'onCityBuildablesScan' payloads as TurnBuildablesScanPayload objects."""
        conditions = ["payload_type = 'onCityBuildablesScan'"]
        params: List[Any] = []

        if player_id is not None:
            conditions.append("CAST(json_data->>'$.player_id' AS INTEGER) = ?")
            params.append(player_id)
        if turn is not None:
            conditions.append("CAST(json_data->>'$.turn' AS INTEGER) = ?")
            params.append(turn)

        where_clause = " WHERE " + " AND ".join(conditions)
        query = "SELECT id, payload_type, json_data, received_at FROM telemetry_records%s ORDER BY id DESC LIMIT ?;" % where_clause
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_tech_tree_scans(self, player_id: Optional[int] = None, limit: int = 50) -> List[TelemetryRecord]:
        """Reads 'onTechTreeScan' payloads as TechTreeScanPayload objects."""
        conditions = ["payload_type = 'onTechTreeScan'"]
        params: List[Any] = []

        if player_id is not None:
            conditions.append("CAST(json_data->>'$.player_id' AS INTEGER) = ?")
            params.append(player_id)

        where_clause = " WHERE " + " AND ".join(conditions)
        query = "SELECT id, payload_type, json_data, received_at FROM telemetry_records%s ORDER BY id DESC LIMIT ?;" % where_clause
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_city_built_events(self, city_name: Optional[str] = None, limit: int = 50) -> List[TelemetryRecord]:
        """Reads 'onCityBuilt' payloads as CityBuiltPayload objects."""
        conditions = ["payload_type = 'onCityBuilt'"]
        params: List[Any] = []

        if city_name:
            conditions.append("json_data->>'$.args.name' = ?")
            params.append(city_name)

        where_clause = " WHERE " + " AND ".join(conditions)
        query = "SELECT id, payload_type, json_data, received_at FROM telemetry_records%s ORDER BY id DESC LIMIT ?;" % where_clause
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_unit_built_events(self, assigned_role: Optional[str] = None, limit: int = 50) -> List[TelemetryRecord]:
        """Reads 'onUnitBuilt' payloads as UnitBuiltPayload objects."""
        conditions = ["payload_type = 'onUnitBuilt'"]
        params: List[Any] = []

        if assigned_role:
            conditions.append("json_data->>'$.unit_details.assigned_role' = ?")
            params.append(assigned_role)

        where_clause = " WHERE " + " AND ".join(conditions)
        query = "SELECT id, payload_type, json_data, received_at FROM telemetry_records%s ORDER BY id DESC LIMIT ?;" % where_clause
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_city_do_turn_events(self, min_food: Optional[int] = None, limit: int = 50) -> List[TelemetryRecord]:
        """Reads 'onCityDoTurn' payloads as CityDoTurnPayload objects."""
        conditions = ["payload_type = 'onCityDoTurn'"]
        params: List[Any] = []

        if min_food is not None:
            conditions.append("CAST(json_data->>'$.city_turn_status.food_yield' AS INTEGER) >= ?")
            params.append(min_food)

        where_clause = " WHERE " + " AND ".join(conditions)
        query = "SELECT id, payload_type, json_data, received_at FROM telemetry_records%s ORDER BY id DESC LIMIT ?;" % where_clause
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._parse_row(row) for row in cursor.fetchall()]