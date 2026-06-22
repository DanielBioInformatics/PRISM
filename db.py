import sqlite3
import hashlib
from datetime import datetime
from flask import session
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS protein_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT,
            pdb_id TEXT,
            sequence TEXT,
            length INTEGER,
            weight REAL,
            pi REAL,
            stability TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    for col in ('sequence', 'user_id', 'notes', 'version_group', 'version_num INTEGER DEFAULT 1', 'results_json TEXT'):
        try:
            c.execute(f'ALTER TABLE protein_history ADD COLUMN {col}')
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def get_user_id():
    return session.get('user_id')


def get_history(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, pdb_id, length, weight, stability, timestamp, version_num FROM protein_history WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    data = c.fetchall()
    conn.close()
    return data


def get_versions(user_id, version_group):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, pdb_id, length, weight, stability, timestamp, version_num FROM protein_history WHERE user_id = ? AND version_group = ? ORDER BY version_num ASC', (user_id, version_group))
    data = c.fetchall()
    conn.close()
    return data


def get_all_notes(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, pdb_id, timestamp, notes, length, weight, stability, version_num FROM protein_history WHERE user_id = ? AND notes IS NOT NULL AND notes != "" ORDER BY timestamp DESC', (user_id,))
    data = c.fetchall()
    conn.close()
    return data


def save_entry(user_id, seq, pdb_id, results):
    vg = hashlib.md5(seq.encode()).hexdigest()[:12]
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT MAX(version_num) FROM protein_history WHERE user_id = ? AND version_group = ?', (user_id, vg))
    row = c.fetchone()
    vnum = (row[0] or 0) + 1
    c.execute('''
        INSERT INTO protein_history (user_id, timestamp, pdb_id, sequence, length, weight, pi, stability, notes, version_group, version_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        pdb_id if pdb_id else "N/A",
        seq,
        results['length'],
        results['weight'],
        results['pi'],
        results['stability_status'],
        "",
        vg,
        vnum
    ))
    conn.commit()
    entry_id = c.lastrowid
    conn.close()
    return entry_id, vg


def load_entry(entry_id, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT ph.sequence, ph.pdb_id, ph.notes FROM protein_history ph WHERE ph.id = ? AND ph.user_id = ?', (entry_id, user_id))
    row = c.fetchone()
    conn.close()
    return row
