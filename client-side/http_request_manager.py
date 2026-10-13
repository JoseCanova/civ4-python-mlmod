# http_request_manager.py
# Centralized HTTP Request Manager for Civilization IV Python Framework
# Python 2.4 & Python 3 Universal Compatibility

import sys
import socket

try:
    import httplib
except ImportError:
    try:
        import http.client as httplib
    except ImportError:
        httplib = None

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = None

if sys.version_info[0] < 3:
    PRIMITIVE_TYPES = (int, long, float, bool, str, unicode)
else:
    PRIMITIVE_TYPES = (int, float, bool, str, bytes)


class HttpRequestManager(object):
    """
    Centralized HTTP Request Manager for Civilization IV Python scripts.
    Handles connectivity checks, GET requests, JSON POST serialization,
    and automatic socket timeout management with strict Python 2.4 compatibility.
    """

    def __init__(self, host="localhost", port=8000, default_endpoint="/api", timeout=2.0):
        self.host = host
        self.port = port
        self.default_endpoint = default_endpoint
        self.timeout = timeout
        self.server_online = False

        # Verify initial connectivity
        self.check_server()

    def set_timeout(self, timeout):
        self.timeout = timeout

    def check_server(self, health_endpoint="/"):
        """
        Verifies if the HTTP server at host:port is reachable.
        Updates self.server_online status and returns boolean.
        """
        if httplib is None:
            print "HttpRequestManager: httplib module is not available."
            self.server_online = False
            return False

        old_timeout = None
        if hasattr(socket, 'getdefaulttimeout'):
            old_timeout = socket.getdefaulttimeout()
        if hasattr(socket, 'setdefaulttimeout'):
            socket.setdefaulttimeout(self.timeout)

        try:
            try:
                conn = httplib.HTTPConnection(self.host, self.port)
                conn.request("GET", health_endpoint)
                response = conn.getresponse()
                conn.close()

                if response.status in (200, 201, 202, 204):
                    self.server_online = True
                    print "HttpRequestManager: Connected to %s:%d (Status: %d)." % (
                        self.host, self.port, response.status
                    )
                    return True
                else:
                    self.server_online = False
                    print "HttpRequestManager: Server at %s:%d returned error status %d." % (
                        self.host, self.port, response.status
                    )
                    return False
            except Exception, e:
                self.server_online = False
                print "HttpRequestManager: Server at %s:%d is OFFLINE (%s)." % (
                    self.host, self.port, str(e)
                )
                return False
        finally:
            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(old_timeout)

    def send_get(self, endpoint="/"):
        """
        Executes an HTTP GET request to the specified endpoint.
        Returns a tuple: (success_bool, status_code, response_body_str).
        """
        if httplib is None:
            return (False, 0, "")

        old_timeout = None
        if hasattr(socket, 'getdefaulttimeout'):
            old_timeout = socket.getdefaulttimeout()
        if hasattr(socket, 'setdefaulttimeout'):
            socket.setdefaulttimeout(self.timeout)

        try:
            try:
                conn = httplib.HTTPConnection(self.host, self.port)
                conn.request("GET", endpoint)
                response = conn.getresponse()
                body = response.read()
                conn.close()

                if response.status in (200, 201, 202, 204):
                    self.server_online = True
                    return (True, response.status, body)
                else:
                    return (False, response.status, body)
            except Exception, e:
                self.server_online = False
                print "HttpRequestManager Warning: GET request to %s failed (%s)." % (endpoint, str(e))
                return (False, 0, "")
        finally:
            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(old_timeout)

    def send_post(self, payload, endpoint=None):
        """
        Posts a Python dict/list as UTF-8 encoded JSON to the HTTP server.
        If endpoint is None, uses self.default_endpoint.
        Returns boolean indicating success.
        """
        if httplib is None or json is None:
            print "HttpRequestManager: Missing required networking or JSON modules."
            return False

        if endpoint is None:
            target_endpoint = self.default_endpoint
        else:
            target_endpoint = endpoint

        old_timeout = None
        if hasattr(socket, 'getdefaulttimeout'):
            old_timeout = socket.getdefaulttimeout()
        if hasattr(socket, 'setdefaulttimeout'):
            socket.setdefaulttimeout(self.timeout)

        try:
            try:
                json_str = json.dumps(payload, ensure_ascii=False)
                if hasattr(json_str, 'encode'):
                    json_bytes = json_str.encode('utf-8')
                else:
                    json_bytes = str(json_str)

                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Length": str(len(json_bytes))
                }

                conn = httplib.HTTPConnection(self.host, self.port)
                conn.request("POST", target_endpoint, json_bytes, headers)
                response = conn.getresponse()
                conn.close()

                if response.status in (200, 201, 202, 204):
                    self.server_online = True
                    print "HttpRequestManager: POST to %s succeeded (HTTP %d)." % (
                        target_endpoint, response.status
                    )
                    return True
                else:
                    print "HttpRequestManager: POST to %s failed with status %d." % (
                        target_endpoint, response.status
                    )
                    return False
            except Exception, e:
                self.server_online = False
                print "HttpRequestManager Warning: POST to %s failed (%s)." % (target_endpoint, str(e))
                return False
        finally:
            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(old_timeout)

    def serialize_item(self, item):
        """
        Converts Civ IV engine objects (CyCity, CyUnit) or basic types into JSON-serializable structures.
        """
        if item is None:
            return None
        if isinstance(item, PRIMITIVE_TYPES):
            return item

        # CyCity object
        if hasattr(item, 'getName') and hasattr(item, 'getOwner') and hasattr(item, 'getPopulation'):
            try:
                iX = -1
                iY = -1
                iID = -1
                if hasattr(item, 'getX'):
                    iX = item.getX()
                if hasattr(item, 'getY'):
                    iY = item.getY()
                if hasattr(item, 'getID'):
                    iID = item.getID()

                return {
                    "_type": "CyCity",
                    "name": item.getName(),
                    "owner": item.getOwner(),
                    "population": item.getPopulation(),
                    "x": iX,
                    "y": iY,
                    "id": iID
                }
            except Exception, e:
                pass

        # CyUnit object
        if hasattr(item, 'getName') and hasattr(item, 'getOwner') and hasattr(item, 'getUnitType'):
            try:
                iX = -1
                iY = -1
                iID = -1
                if hasattr(item, 'getX'):
                    iX = item.getX()
                if hasattr(item, 'getY'):
                    iY = item.getY()
                if hasattr(item, 'getID'):
                    iID = item.getID()

                return {
                    "_type": "CyUnit",
                    "name": item.getName(),
                    "owner": item.getOwner(),
                    "unit_type": item.getUnitType(),
                    "x": iX,
                    "y": iY,
                    "id": iID
                }
            except Exception, e:
                pass

        return str(item)

    def serialize_args_list(self, argsList):
        """Serializes a tuple/list of Civ IV engine arguments."""
        if not argsList:
            return []
        serialized = []
        for item in argsList:
            serialized.append(self.serialize_item(item))
        return serialized

    def post_event(self, event_name, argsList=None, extra_data=None):
        """
        Convenience method to construct and post a structured event payload.
        """
        serialized_args = self.serialize_args_list(argsList)

        payload = {
            "event": event_name,
            "args": serialized_args
        }

        if extra_data and isinstance(extra_data, dict):
            for k in extra_data:
                payload[k] = extra_data[k]

        return self.send_post(payload)
