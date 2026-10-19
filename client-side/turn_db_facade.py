# turn_db_facade.py
# Python 2.4 Compatible Berkeley DB Facade Class for Civilization IV

import os
import sys

# Append custom Berkeley DB Python library path
sys.path.append("E:\\berkleydb\\python")

try:
    import bsddb
except ImportError:
    print "import error on berkleydb"
try:
    import simplejson as json
except ImportError:
    print "import error on simplejson"
    try:
        import json
    except ImportError:
        json = None


class TurnDatabaseFacade(object):
    """
    Facade class that wraps Berkeley DB (bsddb) to expose a key/value store
    allowing multiple data values under the same key ('turn_%d').
    Recreates the database on initialization.
    Strict Python 2.4 compatibility - NO ternary operators used.
    """

    def __init__(self, db_filename="turn_store.db"):
        self.db_filename = db_filename

        # 1. Recreate database on initialization: remove existing file if present
        if os.path.exists(self.db_filename):
            try:
                os.remove(self.db_filename)
            except Exception, e:
                pass

        # 2. Initialize low-level Berkeley DB object
        self.db = bsddb.db.DB()

        # 3. Enable native duplicate keys flag (DB_DUP)
        self.db.set_flags(bsddb.db.DB_DUP)

        # 4. Open B-Tree database with DB_CREATE flag
        self.db.open(self.db_filename, None, bsddb.db.DB_BTREE, bsddb.db.DB_CREATE)

        print "TurnDatabaseFacade: Recreated database file '%s' with DB_DUP support." % self.db_filename

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

        if json is not None and isinstance(data, (dict, list)):
            val_str = json.dumps(data)
        else:
            val_str = str(data)

        # In Berkeley DB with DB_DUP enabled, put() appends duplicate values for the same key
        self.db.put(key, val_str)
        self.db.sync()

    def append(self, turn_number, data):
        """Alias method for insert()."""
        self.insert(turn_number, data)

    def get_turn_records(self, turn_number):
        key = self._format_key(turn_number)
        records = []

        cursor = self.db.cursor()
        try:
            # Catch DB_NOT_FOUND when the key doesn't exist yet
            try:
                rec = cursor.get(key, bsddb.db.DB_SET)
            except bsddb.db.DBNotFoundError:
                rec = None

            while rec:
                val_str = rec[1]
                if json is not None:
                    try:
                        parsed_data = json.loads(val_str)
                        records.append(parsed_data)
                    except Exception:
                        records.append(val_str)
                else:
                    records.append(val_str)

                # Move to next duplicate entry for this key
                try:
                    rec = cursor.next_dup()
                except bsddb.db.DBNotFoundError:
                    rec = None
        finally:
            cursor.close()

        return records


    def sync(self):
        """Flushes database buffers to disk."""
        if self.db:
            self.db.sync()

    def close(self):
        """Closes the Berkeley DB database cleanly."""
        if self.db:
            try:
                self.db.close()
                print "TurnDatabaseFacade: Closed database '%s'." % self.db_filename
            except Exception, e:
                pass
