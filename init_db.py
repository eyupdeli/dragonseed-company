# Rebuilds guild.db from scratch with the sample data required by the exam text.
# Usage: python init_db.py
import os
import sqlite3
from werkzeug.security import generate_password_hash

path = os.path.join(os.path.dirname(__file__), 'guild.db')
if os.path.exists(path):
    os.remove(path)

db = sqlite3.connect(path)
db.executescript('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'adventurer'
);

CREATE TABLE quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    duration INTEGER NOT NULL,
    description TEXT NOT NULL,
    image TEXT NOT NULL
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL REFERENCES quests(id),
    day INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE participations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL,
    places INTEGER NOT NULL CHECK (places IN (1, 2)),  -- backs up the "max 2 places" rule at the db level
    UNIQUE (session_id, user_id)  -- backs up the "can't join the same session twice" rule at the db level
);
''')

# every sample account uses the same password, listed in the README
pw = generate_password_hash('northRemembers')
users = [('guildmaster', 'master'), ('council', 'council'), ('rhaenyra', 'adventurer'),
         ('daemon', 'adventurer'), ('aemond', 'adventurer'), ('jacaerys', 'adventurer')]
db.executemany('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
               [(name, pw, role) for name, role in users])

quests = [
    ('Riddle of the Riderless Dragon', 'puzzle', 'medium', 90,
     'A wild dragon has been circling Driftmark for three days without a rider. The old bloodline '
     'songs say it can be claimed - but only by whoever solves the riddle carved into its lair first.',
     'riddle.jpg'),
    ('Duel Above the Gullet', 'combat', 'hard', 120,
     'Two rival dragonseeds both claim the same beast. Only a duel above the churning strait of the '
     'Gullet will settle whose blood the dragon answers to.',
     'duel.jpg'),
    ('Flight to the Dragonmont', 'exploration', 'legendary', 150,
     'Beyond the smoking peaks of the Dragonmont lies a nest no rider has reached and returned from. '
     'Chart the path, survive the ash winds, and bring back proof you were there.',
     'flight.jpg'),
    ("Smuggler's Run to Driftmark", 'stealth', 'easy', 60,
     'A shipment of dragon eggs is being smuggled out of Driftmark harbour under cover of night. Slip '
     'past the harbour watch, find the crates, and get out before the horns sound.',
     'smuggler.jpg'),
    ('Storm Over the Gullet', 'survival', 'hard', 100,
     'A storm is rolling in over the Gullet and the fishing fleet is still out. Hold the signal fire '
     'until dawn and keep the boats from running onto the rocks.',
     'storm.jpg'),
    ("The Maester's Forbidden Scrolls", 'magic', 'medium', 75,
     "Pages of a maester's banned dragon-lore are scattered across Dragonmont Eyrie. Gather them, "
     'decipher the old Valyrian, and try not to wake anything that is still sleeping up there.',
     'scrolls.jpg'),
]
db.executemany('''INSERT INTO quests (title, type, difficulty, duration, description, image)
                  VALUES (?, ?, ?, ?, ?, ?)''', quests)

SC, MQ, PR = 'Driftmark Shores', 'The Gullet Straits', 'Dragonmont Eyrie'
# two sessions per day; the simulated "now" is Wednesday 17:00,
# so Monday, Tuesday and Wednesday morning are already in the past
sessions = [
    (1, 0, '10:00', SC), (4, 0, '18:00', PR),   # Monday      -> ids 1, 2
    (2, 1, '11:00', MQ), (6, 1, '19:00', SC),   # Tuesday     -> ids 3, 4
    (3, 2, '09:00', MQ), (5, 2, '21:00', PR),   # Wednesday   -> ids 5, 6
    (1, 3, '14:00', SC), (2, 3, '20:00', MQ),   # Thursday    -> ids 7, 8
    (4, 4, '10:00', PR), (6, 4, '17:00', SC),   # Friday      -> ids 9, 10
    (3, 5, '15:00', MQ), (5, 5, '22:00', PR),   # Saturday    -> ids 11, 12
    (1, 6, '11:00', SC), (2, 6, '16:00', MQ),   # Sunday      -> ids 13, 14
]
db.executemany('INSERT INTO sessions (quest_id, day, start_time, location) VALUES (?, ?, ?, ?)',
               sessions)

# user ids: 3 = rhaenyra, 4 = daemon, 5 = aemond, 6 = jacaerys
participations = [
    (8, 3, 'Healer', 2),     # rhaenyra takes both Healer places on Thu 20:00 -> role fully booked
    (8, 5, 'Warrior', 1),    # aemond, same session, still modifiable
    (2, 4, 'Mage', 1),       # daemon, Monday session already over -> locked
    (6, 4, 'Warrior', 1),    # daemon, Wed 21:00 starts in 4 hours -> locked by the 8h rule
    (6, 6, 'Healer', 1),     # jacaerys, same locked session
    (11, 5, 'Mage', 2),      # aemond, Saturday -> modifiable
    (12, 6, 'Warrior', 2),   # jacaerys, Saturday -> modifiable
]
db.executemany('INSERT INTO participations (session_id, user_id, role, places) VALUES (?, ?, ?, ?)',
               participations)

db.commit()
db.close()
print('guild.db ready:', len(users), 'users,', len(quests), 'quests,',
      len(sessions), 'sessions,', len(participations), 'participations.')
