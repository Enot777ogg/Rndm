import sqlite3

def init_db():
    conn = sqlite3.connect("rndm.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contests (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            photo_id TEXT,
            datetime TEXT,
            group_name TEXT,
            creator TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            contest_id TEXT,
            user_id INTEGER,
            UNIQUE(contest_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_contest(cid, title, desc, photo, dt, group, creator):
    conn = sqlite3.connect("rndm.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO contests VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (cid, title, desc, photo, dt, group, creator))
    conn.commit()
    conn.close()

def add_participant(cid, user_id):
    conn = sqlite3.connect("rndm.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO participants VALUES (?, ?)", (cid, user_id))
    conn.commit()
    conn.close()

def get_participants(cid):
    conn = sqlite3.connect("rndm.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM participants WHERE contest_id = ?", (cid,))
    result = cursor.fetchall()
    conn.close()
    return [r[0] for r in result]
