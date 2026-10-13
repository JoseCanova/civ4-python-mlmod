from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import json
import server_data_models_v3 as server_data_models
from civ4_json_db import Civ4JsonTelemetryDatabase

db = Civ4JsonTelemetryDatabase()

# Define a multi-threaded server class by inheriting ThreadingMixIn
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# --- Handler 1: Handles API requests ---
class ApiHandler:
    @staticmethod
    def handle_get(handler_instance):
        handler_instance.send_response(200)
        handler_instance.send_header("Content-type", "application/json")
        handler_instance.end_headers()
        handler_instance.wfile.write(b'{"route": "api", "status": "active"}')

    @staticmethod
    def handle_post(handler_instance):
        try:
            content_length = int(handler_instance.headers.get("Content-Length", 0))
            if content_length == 0:
                handler_instance.send_response(400)
                handler_instance.end_headers()
                handler_instance.wfile.write(b'{"error": "Empty body"}')
                return

            # Read raw JSON bytes directly from the request
            raw_bytes = handler_instance.rfile.read(content_length)
            body_str = raw_bytes.decode("utf-8")
            
            # Optional: quick check to parse JSON structure
            json_data = json.loads(body_str)
            payload_type = json_data.get("type", "generic_telemetry")

            # Store the raw JSON string straight into SQLite
            record_id = db.save_payload(payload_type, body_str)

            handler_instance.send_response(200)
            handler_instance.send_header("Content-type", "application/json")
            handler_instance.end_headers()
            handler_instance.wfile.write(
                json.dumps({"status": "success", "record_id": record_id}).encode("utf-8")
            )

        except json.JSONDecodeError:
            handler_instance.send_response(400)
            handler_instance.end_headers()
            handler_instance.wfile.write(b'{"error": "Invalid JSON"}')


# --- Handler 2: Handles Website / HTML requests ---
class WebHandler:
    @staticmethod
    def handle_get(handler_instance):
        handler_instance.send_response(200)
        handler_instance.send_header("Content-type", "text/html; charset=utf-8")
        handler_instance.end_headers()
        handler_instance.wfile.write(b"<h1>Welcome to the Home Page!</h1>")

# --- Master Dispatcher Handler ---
class RouterMasterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Route GET requests
        if self.path.startswith("/api"):
            ApiHandler.handle_get(self)
        elif self.path == "/" or self.path.startswith("/web"):
            WebHandler.handle_get(self)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Custom 404: Route Not Found")

    def do_POST(self):
        # Route POST requests
        if self.path.startswith("/api"):
            ApiHandler.handle_post(self)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Custom 404: POST Route Not Found")

def run(port=8000):
    server_address = ("", port)
    # Instantiate ThreadingHTTPServer instead of single-threaded HTTPServer
    http_server = ThreadingHTTPServer(server_address, RouterMasterHandler)
    print(f"Multi-threaded server running on port {port}...")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        http_server.server_close()

if __name__ == "__main__":
    run()
