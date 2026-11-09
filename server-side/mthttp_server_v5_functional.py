# mthttp_server_v5_functional.py
"""
Functional Multi-Threaded HTTP Server (v5 Architecture)
Refactored into a Functional Programming (FP) style while maintaining exact imperative logic.
"""

import os
import json
import sqlite3
from typing import Callable, Dict, Any, Tuple, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import functools

# Import server_data_models v8
import server_data_models_v8 as models
from server_data_models_v8 import PayloadDispatcher

# --- Configuration & Environment (Immutable Defaults) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "civ4_telemetry_json.db")

# ==============================================================================
# 1. PURE DATABASE & I/O SIDE-EFFECT FUNCTIONS
# ==============================================================================

def init_db(db_path: str = DEFAULT_DB_PATH) -> str:
    """Side effect: Ensures database schema exists and returns db_path."""
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_type TEXT NOT NULL,
                json_data TEXT NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    return db_path


def save_raw_payload(db_path: str, payload_type: str, raw_body: str) -> int:
    """Side effect: Saves raw JSON payload string into SQLite document table."""
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO telemetry_records (payload_type, json_data) VALUES (?, ?)",
            (payload_type, raw_body)
        )
        conn.commit()
        return cursor.lastrowid


def save_model_batch(parsed_model: Any, db_path: str) -> int:
    """Side effect: Triggers model-level SQLite batch persistence if supported."""
    if parsed_model and hasattr(parsed_model, "save_to_sqlite"):
        try:
            return parsed_model.save_to_sqlite(db_path)
        except Exception as sq_err:
            print(f"[SERVER ERROR] Failed SQLite batch ingestion: {sq_err}")
            return 0
    return 0


# ==============================================================================
# 2. PURE DATA TRANSFORMATION PIPELINE FUNCTIONS
# ==============================================================================

def extract_payload_type(json_data: dict) -> str:
    """Pure function: Extracts payload event type from JSON dictionary."""
    return json_data.get("event", json_data.get("type", "generic_telemetry"))


def extract_model_summary(parsed_model: Any) -> Tuple[str, str]:
    """Pure function: Extracts (model_class_name, summary_text)."""
    if not parsed_model:
        return ("None", "")
    class_name = parsed_model.__class__.__name__
    summary = parsed_model.summary() if hasattr(parsed_model, "summary") else ""
    return (class_name, summary)


def build_response_payload(
    status: str,
    record_id: int,
    payload_type: str,
    model_class_name: str,
    unbatched_count: int,
    summary_output: str
) -> Dict[str, Any]:
    """Pure function: Constructs standard API response dictionary."""
    return {
        "status": status,
        "record_id": record_id,
        "payload_type": payload_type,
        "parsed_model_class": model_class_name,
        "sqlite_unbatched_records": unbatched_count,
        "summary": summary_output
    }


def process_telemetry_post(db_path: str, raw_body_str: str) -> Tuple[int, Dict[str, Any]]:
    """
    Pure orchestration pipeline function:
    Transforms raw JSON body string into (HTTP_STATUS, RESPONSE_DICT) tuple.
    """
    # 1. Parse JSON payload
    json_data = json.loads(raw_body_str)

    # 2. Extract event type & dispatch model
    payload_type = extract_payload_type(json_data)
    parsed_model = PayloadDispatcher.parse_payload(json_data)

    # 3. Side Effect Boundaries (Batch DB Save & Raw DB Save)
    sqlite_unbatched_count = save_model_batch(parsed_model, db_path)
    model_class_name, summary_output = extract_model_summary(parsed_model)

    if summary_output:
        print(f"\n[SERVER DISPATCHER - {model_class_name}]\n{summary_output}\n" + "-" * 50)

    record_id = save_raw_payload(db_path, payload_type, raw_body_str)

    # 4. Pure Response Construction
    response_payload = build_response_payload(
        status="success",
        record_id=record_id,
        payload_type=payload_type,
        model_class_name=model_class_name,
        unbatched_count=sqlite_unbatched_count,
        summary_output=summary_output
    )

    return (200, response_payload)


# ==============================================================================
# 3. FUNCTION DECORATORS (CROSS-CUTTING CONCERNS)
# ==============================================================================

def json_response_adapter(handler_func: Callable) -> Callable:
    """
    Higher-Order Function / Decorator:
    Wraps a pure logic function returning (status_code, dict) into an HTTP writer.
    """
    @functools.wraps(handler_func)
    def wrapper(handler_instance, *args, **kwargs):
        try:
            status_code, response_data = handler_func(handler_instance, *args, **kwargs)
            response_bytes = json.dumps(response_data, indent=2).encode("utf-8")
            
            handler_instance.send_response(status_code)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            handler_instance.wfile.write(response_bytes)
        except json.JSONDecodeError:
            handler_instance.send_response(400)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            handler_instance.wfile.write(b'{"error": "Invalid JSON payload"}')
        except Exception as err:
            handler_instance.send_response(500)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            err_msg = json.dumps({"error": f"Internal Server Error: {str(err)}"}).encode("utf-8")
            handler_instance.wfile.write(err_msg)
    return wrapper


# ==============================================================================
# 4. FUNCTIONAL ROUTE HANDLERS
# ==============================================================================

@json_response_adapter
def handle_api_get(handler_instance: BaseHTTPRequestHandler) -> Tuple[int, Dict[str, Any]]:
    """Pure Handler for GET /api requests."""
    return (200, {
        "route": "api",
        "status": "active",
        "models_version": "v5",
        "supported_events": [
            "onTurnBatch", "onCityBuildablesScan", "onTechTreeScan",
            "onCityBuilt", "onUnitBuilt", "onCityDoTurn"
        ]
    })


@json_response_adapter
def handle_api_post(db_path: str, handler_instance: BaseHTTPRequestHandler) -> Tuple[int, Dict[str, Any]]:
    """Handler for POST /api requests with dependency-injected db_path."""
    content_length = int(handler_instance.headers.get("Content-Length", 0))
    if content_length == 0:
        return (400, {"error": "Empty body or missing Content-Length"})

    raw_bytes = handler_instance.rfile.read(content_length)
    body_str = raw_bytes.decode("utf-8")

    return process_telemetry_post(db_path, body_str)


def handle_web_get(handler_instance: BaseHTTPRequestHandler) -> None:
    """HTML Response Handler."""
    handler_instance.send_response(200)
    handler_instance.send_header("Content-type", "text/html; charset=utf-8")
    handler_instance.end_headers()
    handler_instance.wfile.write(b"<h1>Civ IV Telemetry Server (v5 Models with FP Refactoring)</h1>")


def handle_404(handler_instance: BaseHTTPRequestHandler) -> None:
    """Fallback 404 Handler."""
    handler_instance.send_response(404)
    handler_instance.end_headers()
    handler_instance.wfile.write(b"Custom 404: Route Not Found")


# ==============================================================================
# 5. DECLARATIVE FUNCTIONAL ROUTER & SERVER SETUP
# ==============================================================================

def create_router(db_path: str) -> Callable[[str, str], Callable[[BaseHTTPRequestHandler], None]]:
    """
    Higher-Order Function returning a functional path dispatcher closure.
    Replaces imperative if/elif chains with declarative data matching.
    """
    # Partial application injects db_path into post handler
    configured_api_post = functools.partial(handle_api_post, db_path)

    # Route table mapping (HTTP_METHOD, PATH_MATCH_PREDICATE) -> HANDLER
    routes = [
        ("GET", lambda p: p.startswith("/api"), handle_api_get),
        ("POST", lambda p: p.startswith("/api"), configured_api_post),
        ("GET", lambda p: p == "/" or p.startswith("/web"), handle_web_get),
    ]

    def dispatch(method: str, path: str) -> Callable[[BaseHTTPRequestHandler], None]:
        # Declarative functional lookup using next() and filter()
        matched_handler = next(
            (handler for req_method, predicate, handler in routes if req_method == method and predicate(path)),
            handle_404
        )
        return matched_handler

    return dispatch


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def make_request_handler(router_dispatcher: Callable) -> type:
    """
    Factory creating a BaseHTTPRequestHandler class bound to a functional router.
    """
    class FunctionalRouterHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            handler = router_dispatcher("GET", self.path)
            handler(self)

        def do_POST(self):
            handler = router_dispatcher("POST", self.path)
            handler(self)

        def log_message(self, format, *args):
            return

    return FunctionalRouterHandler


def run(port: int = 8000, db_path: str = DEFAULT_DB_PATH) -> None:
    # 1. Initialize DB side effect
    active_db_path = init_db(db_path)

    # 2. Build functional router closure with dependency injection
    router_dispatcher = create_router(active_db_path)
    handler_class = make_request_handler(router_dispatcher)

    # 3. Start server
    server_address = ("", port)
    http_server = ThreadingHTTPServer(server_address, handler_class)
    print(f"Multi-threaded FP Server running on port {port} using server_data_models (v5)...")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        http_server.server_close()


if __name__ == "__main__":
    run()
