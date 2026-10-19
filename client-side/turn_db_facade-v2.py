# turn_db_facade.py
# Python 2.4 Compatible Berkeley DB Facade Class for Civilization IV

import os
import sys

# Append custom Berkeley DB Python library path if needed
# sys.path.append("E:\\berkleydb\\python")

try:
    import bsddb
    HAS_BSDDB = True
except ImportError:
    HAS_BSDDB = False

try:
    import simplejson as json
    HAS_JSON = True
except ImportError:
    try:
        import json
        HAS_JSON = True
    except ImportError:
        json = None
        HAS_JSON = False


class TurnDatabaseFacade(object):
    """
    Facade class that wraps Berkeley DB (bsddb) to expose a key/value store
    allowing multiple data values under the same key ('turn_%d').
    Recreates or manages the database on initialization.
    Supports delete_turn_records() to purge processed events after HTTP submission.
    Strict Python 2.4 compatibility - NO ternary operators used under any circumstance.
    """

    def __init__(self, db_filename="turn_store.db"):
        self.db_filename = db_filename
        self.db = None
        self.in_memory_store = {}

        if HAS_BSDDB:
            # 1. Recreate database on initialization: remove existing file if present
            if os.path.exists(self.db_filename):
                try:
                    os.remove(self.db_filename)
                except Exception:
                    pass

            try:
                self.db = bsddb.db.DB()
                self.db.set_flags(bsddb.db.DB_DUP)
                self.db.open(self.db_filename, None, bsddb.db.DB_BTREE, bsddb.db.DB_CREATE)
                print("TurnDatabaseFacade: Recreated Berkeley DB '%s' with DB_DUP." % self.db_filename)
            except Exception:
                e = sys.exc_info()[1]
                print("TurnDatabaseFacade Warning: Failed initializing bsddb (%s). Falling back to in-memory store." % str(e))
                self.db = None
        else:
            print("TurnDatabaseFacade: Using in-memory store for turn telemetry.")

    def _format_key(self, turn_number):
        """Formats turn integer or string into 'turn_%d' key."""
        if isinstance(turn_number, int):
            return "turn_%d" % turn_number
        else:
            try:
                iTurn = int(turn_number)
                return "turn_%d" % iTurn
            except Exception:
                return str(turn_number)

    def insert(self, turn_number, data):
        """
        Inserts/appends a value under key 'turn_%d'.
        Accepts dicts, lists, or raw strings (dicts/lists serialized as JSON).
        """
        key = self._format_key(turn_number)

        val_str = ""
        if HAS_JSON and json is not None and isinstance(data, (dict, list)):
            val_str = json.dumps(data)
        else:
            val_str = str(data)

        if self.db:
            try:
                self.db.put(key, val_str)
                self.db.sync()
            except Exception:
                e = sys.exc_info()[1]
                print("TurnDatabaseFacade Warning: Failed inserting into DB: %s" % str(e))
        else:
            if key not in self.in_memory_store:
                self.in_memory_store[key] = []
            self.in_memory_store[key].append(val_str)

    def append(self, turn_number, data):
        """Alias method for insert()."""
        self.insert(turn_number, data)

    def get_turn_records(self, turn_number):
        """
        Retrieves all data records stored under 'turn_%d'.
        Returns a list of parsed JSON objects or strings.
        """
        key = self._format_key(turn_number)
        records = []

        if self.db:
            cursor = None
            try:
                cursor = self.db.cursor()
                try:
                    rec = cursor.get(key, bsddb.db.DB_SET)
                except Exception:
                    rec = None

                while rec:
                    val_str = rec[1]
                    if HAS_JSON and json is not None:
                        try:
                            parsed_data = json.loads(val_str)
                            records.append(parsed_data)
                        except Exception:
                            records.append(val_str)
                    else:
                        records.append(val_str)

                    try:
                        rec = cursor.next_dup()
                    except Exception:
                        rec = None
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass
        else:
            if key in self.in_memory_store:
                raw_list = self.in_memory_store[key]
                for val_str in raw_list:
                    if HAS_JSON and json is not None:
                        try:
                            parsed_data = json.loads(val_str)
                            records.append(parsed_data)
                        except Exception:
                            records.append(val_str)
                    else:
                        records.append(val_str)

        return records

    def delete_turn_records(self, turn_number):
        """
        Deletes all data records stored under 'turn_%d'.
        Frees memory and storage space immediately upon successful HTTP submission.
        """
        key = self._format_key(turn_number)
        
        if self.db:
            try:
                self.db.delete(key)
                self.db.sync()
                print("TurnDatabaseFacade: Successfully deleted records for key '%s'." % key)
                return True
            except Exception:
                print("TurnDatabaseFacade: Key '%s' not found or already deleted." % key)
                return True
        else:
            if key in self.in_memory_store:
                del self.in_memory_store[key]
                print("TurnDatabaseFacade: Deleted in-memory records for key '%s'." % key)
                return True
            return False

    def sync(self):
        """Flushes database buffers to disk."""
        if self.db:
            try:
                self.db.sync()
            except Exception:
                pass

    def close(self):
        """Closes the Berkeley DB database cleanly."""
        if self.db:
            try:
                self.db.close()
                print("TurnDatabaseFacade: Closed database '%s'." % self.db_filename)
            except Exception:
                pass
