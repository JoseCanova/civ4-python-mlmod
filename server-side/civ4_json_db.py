import os 
import sqlite3
import json
from typing import Optional, List, Dict, Any, Union

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "civ4_telemetry_json.db")

class Civ4JsonTelemetryDatabase:
    """Manages raw JSON telemetry storage in SQLite using native JSON operators."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Creates a single document-style storage table for JSON telemetry."""
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_type TEXT NOT NULL,
                    json_data TEXT NOT NULL,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def save_payload(self, payload_type: str, data: Union[dict, list, str]) -> int:
        """
        Stores raw incoming JSON directly into the TEXT column.
        Accepts either a parsed Python dict/list or a raw JSON string.
        """
        json_string = data if isinstance(data, str) else json.dumps(data)

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_records (payload_type, json_data) VALUES (?, ?)",
                (payload_type, json_string)
            )
            conn.commit()
            return cursor.lastrowid

    # --- Querying JSON Directly with SQLite JSON Operators ---

    def query_scans_by_player(self, player_id: int) -> List[Dict[str, Any]]:
        """
        Queries buildable scans using:
          - '->>' to extract scalar text/numbers for filtering/SELECT
          - '->'  to extract sub-arrays/objects as raw JSON
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    id,
                    json_data->>'$.turn' AS turn,
                    json_data->>'$.player_id' AS player_id,
                    json_data->'$.cities' AS cities_json,
                    received_at
                FROM telemetry_records
                WHERE payload_type = 'buildable_scan' 
                  AND CAST(json_data->>'$.player_id' AS INTEGER) = ?;
            """
            cursor.execute(query, (player_id,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "turn": int(row["turn"]) if row["turn"] is not None else None,
                    "player_id": int(row["player_id"]) if row["player_id"] is not None else None,
                    "cities": json.loads(row["cities_json"]) if row["cities_json"] else [],
                    "received_at": row["received_at"]
                })
            return results

    def query_events_by_name(self, event_name: str) -> List[Dict[str, Any]]:
        """Filters game events by looking inside the JSON string."""
        with self.connect() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    id,
                    json_data->>'$.event_name' AS event_name,
                    json_data->'$.args' AS args_json,
                    json_data->'$.extra_data' AS extra_data_json
                FROM telemetry_records
                WHERE payload_type = 'game_event'
                  AND json_data->>'$.event_name' = ?;
            """
            cursor.execute(query, (event_name,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "event_name": row["event_name"],
                    "args": json.loads(row["args_json"]) if row["args_json"] else [],
                    "extra_data": json.loads(row["extra_data_json"]) if row["extra_data_json"] else {}
                })
            return results
