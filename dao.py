import sqlite3
import os

# absolute path so the db is found no matter the working directory (needed on PythonAnywhere)
DB = os.path.join(os.path.dirname(__file__), 'guild.db')


def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


# ---------- users ----------

def get_user_by_username(username):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    db.close()
    return user


def get_user_by_id(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    return user


def add_user(username, password_hash):
    db = get_db()
    db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'adventurer')",
               (username, password_hash))
    db.commit()
    db.close()


# ---------- quests ----------

def get_quests():
    db = get_db()
    quests = db.execute('SELECT * FROM quests ORDER BY title').fetchall()
    db.close()
    return quests


def get_quest(quest_id):
    db = get_db()
    quest = db.execute('SELECT * FROM quests WHERE id = ?', (quest_id,)).fetchone()
    db.close()
    return quest


def add_quest(title, qtype, difficulty, duration, description, image):
    db = get_db()
    db.execute('''INSERT INTO quests (title, type, difficulty, duration, description, image)
                  VALUES (?, ?, ?, ?, ?, ?)''',
               (title, qtype, difficulty, duration, description, image))
    db.commit()
    db.close()


# ---------- quest sessions ----------

# get_sessions and get_session both need the same join, so keeping it in one place
SESSION_SELECT = '''SELECT s.id, s.quest_id, s.day, s.start_time, s.location,
                           q.title, q.type, q.difficulty, q.duration, q.image, q.description
                    FROM sessions s JOIN quests q ON s.quest_id = q.id'''


def get_sessions():
    db = get_db()
    rows = db.execute(SESSION_SELECT + ' ORDER BY s.day, s.start_time').fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_session(session_id):
    db = get_db()
    row = db.execute(SESSION_SELECT + ' WHERE s.id = ?', (session_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def add_session(quest_id, day, start_time, location):
    db = get_db()
    db.execute('INSERT INTO sessions (quest_id, day, start_time, location) VALUES (?, ?, ?, ?)',
               (quest_id, day, start_time, location))
    db.commit()
    db.close()


def update_session(session_id, day, start_time, location):
    db = get_db()
    db.execute('UPDATE sessions SET day = ?, start_time = ?, location = ? WHERE id = ?',
               (day, start_time, location, session_id))
    db.commit()
    db.close()


def delete_session(session_id):
    db = get_db()
    db.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
    db.commit()
    db.close()


# ---------- participations ----------

def get_role_counts():
    # reserved places for every (session, role) pair
    db = get_db()
    rows = db.execute('''SELECT session_id, role, SUM(places) AS taken
                         FROM participations GROUP BY session_id, role''').fetchall()
    db.close()
    # keyed by (session_id, role) so app.py can look up one number at a time
    return {(row['session_id'], row['role']): row['taken'] for row in rows}


def count_participants(session_id):
    db = get_db()
    n = db.execute('SELECT COUNT(*) FROM participations WHERE session_id = ?',
                   (session_id,)).fetchone()[0]
    db.close()
    return n


def get_participation(user_id, session_id):
    db = get_db()
    row = db.execute('SELECT * FROM participations WHERE user_id = ? AND session_id = ?',
                     (user_id, session_id)).fetchone()
    db.close()
    return row


def get_participation_by_id(part_id):
    db = get_db()
    row = db.execute('''SELECT p.*, s.day, s.start_time FROM participations p
                        JOIN sessions s ON p.session_id = s.id WHERE p.id = ?''',
                     (part_id,)).fetchone()
    db.close()
    return row


def get_user_participations(user_id):
    db = get_db()
    rows = db.execute('''SELECT p.id, p.role, p.places, s.id AS session_id, s.day,
                                s.start_time, s.location, q.title, q.duration
                         FROM participations p
                         JOIN sessions s ON p.session_id = s.id
                         JOIN quests q ON s.quest_id = q.id
                         WHERE p.user_id = ? ORDER BY s.day, s.start_time''', (user_id,)).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_session_participations(session_id):
    db = get_db()
    rows = db.execute('''SELECT u.username, p.role, p.places FROM participations p
                         JOIN users u ON p.user_id = u.id
                         WHERE p.session_id = ? ORDER BY p.role''', (session_id,)).fetchall()
    db.close()
    return rows


def add_participation(session_id, user_id, role, places):
    db = get_db()
    db.execute('INSERT INTO participations (session_id, user_id, role, places) VALUES (?, ?, ?, ?)',
               (session_id, user_id, role, places))
    db.commit()
    db.close()


def delete_participation(part_id):
    db = get_db()
    db.execute('DELETE FROM participations WHERE id = ?', (part_id,))
    db.commit()
    db.close()


# ---------- guild council statistics ----------

def get_adventurers():
    db = get_db()
    rows = db.execute('''SELECT u.username, COUNT(p.id) AS sessions_joined,
                                COALESCE(SUM(p.places), 0) AS places_reserved
                         FROM users u LEFT JOIN participations p ON p.user_id = u.id
                         WHERE u.role = 'adventurer'
                         GROUP BY u.id ORDER BY u.username''').fetchall()
    db.close()
    return rows


# everything the council's stats page needs, one query per number
def get_platform_stats():
    db = get_db()
    stats = {
        'adventurers': db.execute("SELECT COUNT(*) FROM users WHERE role = 'adventurer'").fetchone()[0],
        'quests': db.execute('SELECT COUNT(*) FROM quests').fetchone()[0],
        'sessions': db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],
        'participations': db.execute('SELECT COUNT(*) FROM participations').fetchone()[0],
        'per_role': db.execute('''SELECT role, SUM(places) AS places FROM participations
                                  GROUP BY role ORDER BY role''').fetchall(),
        'top_type': db.execute('''SELECT q.type, SUM(p.places) AS places FROM participations p
                                  JOIN sessions s ON p.session_id = s.id
                                  JOIN quests q ON s.quest_id = q.id
                                  GROUP BY q.type ORDER BY places DESC LIMIT 1''').fetchone(),
        'top_session': db.execute('''SELECT q.title, s.day, s.start_time, SUM(p.places) AS places
                                     FROM participations p
                                     JOIN sessions s ON p.session_id = s.id
                                     JOIN quests q ON s.quest_id = q.id
                                     GROUP BY s.id ORDER BY places DESC LIMIT 1''').fetchone(),
    }
    db.close()
    return stats
