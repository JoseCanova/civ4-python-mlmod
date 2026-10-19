import turn_db_facade
# Instantiate facade (recreates 'session_turns.db' on disk)
db_facade = turn_db_facade.TurnDatabaseFacade('session_turns.db')

# Insert multiple event records under Turn 1
db_facade.insert(1, {"event": "onCityBuilt", "city": "Rome", "strategy": "GROWTH"})
db_facade.insert(1, {"event": "onUnitBuilt", "unit": "Warrior", "role": "GARRISON"})

# Insert records for Turn 2
db_facade.insert(2, {"event": "onCityDoTurn", "city": "Rome", "project": "Granary"})

# Retrieve all records for Turn 1 (returns list of 2 dicts)
turn_1_events = db_facade.get_turn_records(1)
print "Turn 1 Total Logged Events:", len(turn_1_events)

# Flush and close
db_facade.close()
