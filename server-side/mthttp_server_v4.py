import os
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Import server_data_models_v4 and PayloadDispatcher
import server_data_models_v4 as server_data_models
from server_data_models_v4 import PayloadDispatcher

# --- SQLite Document Database Integration ---
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

    def save_payload(self, payload_type: str, data: str) -> int:
        """Stores raw incoming JSON directly into the TEXT column."""
        json_string = data if isinstance(data, str) else json.dumps(data)
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_records (payload_type, json_data) VALUES (?, ?)",
                (payload_type, json_string)
            )
            conn.commit()
            return cursor.lastrowid

# Global Database Instance
db = Civ4JsonTelemetryDatabase()

# --- Multi-Threaded HTTP Server ---
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handles each HTTP request in a separate thread without blocking."""
    daemon_threads = True

# --- API Route Handler ---
class ApiHandler:
    @staticmethod
    def handle_get(handler_instance):
        handler_instance.send_response(200)
        handler_instance.send_header("Content-type", "application/json")
        handler_instance.end_headers()
        handler_instance.wfile.write(b'{"route": "api", "status": "active", "models_version": "v4"}')

    @staticmethod
    def handle_post(handler_instance):
        try:
            # 1. Read Content-Length header
            content_length = int(handler_instance.headers.get("Content-Length", 0))
            if content_length == 0:
                handler_instance.send_response(400)
                handler_instance.send_header("Content-type", "application/json")
                handler_instance.end_headers()
                handler_instance.wfile.write(b'{"error": "Empty body or missing Content-Length"}')
                return

            # 2. Read raw bytes and decode string
            raw_bytes = handler_instance.rfile.read(content_length)
            body_str = raw_bytes.decode("utf-8")

            # 3. Parse JSON dictionary
            json_data = json.loads(body_str)
            payload_type = json_data.get("event", json_data.get("type", "generic_telemetry"))

            # 4. Dispatch and parse model using server_data_models_v4.PayloadDispatcher
            parsed_model = PayloadDispatcher.parse_payload(json_data)

            # 5. Inspect and extract summary output
            summary_output = ""
            model_class_name = "None"
            if parsed_model:
                model_class_name = parsed_model.__class__.__name__
                if hasattr(parsed_model, "summary"):
                    summary_output = parsed_model.summary()
                    # Console log summary inspection
                    print(f"\n[SERVER DISPATCHER - {model_class_name}]")
                    print(summary_output)
                    print("-" * 50)

            # 6. Save raw JSON payload into SQLite database
            record_id = db.save_payload(payload_type, body_str)

            # 7. Respond with JSON telemetry inspection report
            response_payload = {
                "status": "success",
                "record_id": record_id,
                "payload_type": payload_type,
                "parsed_model_class": model_class_name,
                "summary": summary_output
            }

            response_bytes = json.dumps(response_payload, indent=2).encode("utf-8")
            handler_instance.send_response(200)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            handler_instance.wfile.write(response_bytes)

        except json.JSONDecodeError:
            handler_instance.send_response(400)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            handler_instance.wfile.write(b'{"error": "Invalid JSON payload"}')

# --- Website HTML Route Handler ---
class WebHandler:
    @staticmethod
    def handle_get(handler_instance):
        handler_instance.send_response(200)
        handler_instance.send_header("Content-type", "text/html; charset=utf-8")
        handler_instance.end_headers()
        handler_instance.wfile.write(b"<h1>Civ IV Telemetry Server (v4 Models)</h1>")

# --- Master Dispatcher Handler ---
class RouterMasterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api"):
            ApiHandler.handle_get(self)
        elif self.path == "/" or self.path.startswith("/web"):
            WebHandler.handle_get(self)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Custom 404: Route Not Found")

    def do_POST(self):
        if self.path.startswith("/api"):
            ApiHandler.handle_post(self)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Custom 404: POST Route Not Found")

def run(port=8000):
    server_address = ("", port)
    http_server = ThreadingHTTPServer(server_address, RouterMasterHandler)
    print(f"Multi-threaded Civ IV Server running on port {port} using server_data_models_v4...")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        http_server.server_close()

if __name__ == "__main__":
    run()
