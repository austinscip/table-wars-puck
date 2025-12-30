"""
TABLE WARS - Database Abstraction Layer
Supports both SQLite (local dev) and PostgreSQL (production)
"""

import os
from datetime import datetime
from contextlib import contextmanager

# Determine which database to use
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
    print("✅ Using PostgreSQL")
else:
    import sqlite3
    print("✅ Using SQLite (local dev)")

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

@contextmanager
def get_db_connection():
    """Get database connection (context manager for auto-close)"""
    if USE_POSTGRES:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect('tablewars.db')
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Initialize database tables (works for both SQLite and PostgreSQL)"""

    with get_db_connection() as conn:
        c = conn.cursor()

        # Bars table
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS bars (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                location TEXT,
                total_tables INTEGER DEFAULT 4,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                location TEXT,
                total_tables INTEGER DEFAULT 4,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )''')

        # Pucks table
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS pucks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                bar_id INTEGER REFERENCES bars(id),
                table_number INTEGER,
                battery_level INTEGER,
                is_online BOOLEAN DEFAULT TRUE,
                last_seen TIMESTAMP,
                total_games_played INTEGER DEFAULT 0
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS pucks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                bar_id INTEGER,
                table_number INTEGER,
                battery_level INTEGER,
                is_online BOOLEAN DEFAULT 1,
                last_seen TIMESTAMP,
                total_games_played INTEGER DEFAULT 0,
                FOREIGN KEY (bar_id) REFERENCES bars(id)
            )''')

        # Games table
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                bar_id INTEGER REFERENCES bars(id),
                puck_id INTEGER,
                game_id INTEGER,
                game_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bar_id INTEGER,
                puck_id INTEGER,
                game_id INTEGER,
                game_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                FOREIGN KEY (bar_id) REFERENCES bars(id),
                FOREIGN KEY (puck_id) REFERENCES pucks(id)
            )''')

        # Sessions table
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                bar_id INTEGER REFERENCES bars(id),
                table_number INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                total_pucks INTEGER,
                is_active BOOLEAN DEFAULT TRUE
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                bar_id INTEGER,
                table_number INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                total_pucks INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (bar_id) REFERENCES bars(id)
            )''')

        # Active games table
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS active_games (
                id SERIAL PRIMARY KEY,
                bar_id INTEGER REFERENCES bars(id),
                table_number INTEGER,
                puck_id INTEGER,
                game_id INTEGER,
                game_name TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS active_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bar_id INTEGER,
                table_number INTEGER,
                puck_id INTEGER,
                game_id INTEGER,
                game_name TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bar_id) REFERENCES bars(id)
            )''')

        # Create leaderboard view (different for each DB)
        if USE_POSTGRES:
            c.execute('''CREATE OR REPLACE VIEW leaderboard AS
                SELECT
                    p.id,
                    p.name,
                    p.bar_id,
                    p.table_number,
                    b.name as bar_name,
                    COUNT(g.id) as games_played,
                    COALESCE(SUM(g.score), 0) as total_score,
                    COALESCE(AVG(g.score), 0) as avg_score,
                    COALESCE(MAX(g.score), 0) as high_score,
                    MAX(g.timestamp) as last_played
                FROM pucks p
                LEFT JOIN games g ON p.id = g.puck_id
                LEFT JOIN bars b ON p.bar_id = b.id
                GROUP BY p.id, p.name, p.bar_id, p.table_number, b.name
                ORDER BY total_score DESC
            ''')
        else:
            c.execute('''CREATE VIEW IF NOT EXISTS leaderboard AS
                SELECT
                    p.id,
                    p.name,
                    p.bar_id,
                    p.table_number,
                    b.name as bar_name,
                    COUNT(g.id) as games_played,
                    SUM(g.score) as total_score,
                    AVG(g.score) as avg_score,
                    MAX(g.score) as high_score,
                    MAX(g.timestamp) as last_played
                FROM pucks p
                LEFT JOIN games g ON p.id = g.puck_id
                LEFT JOIN bars b ON p.bar_id = b.id
                GROUP BY p.id
                ORDER BY total_score DESC
            ''')

        # Insert demo bar if none exists
        c.execute("SELECT COUNT(*) FROM bars")
        count = c.fetchone()

        if USE_POSTGRES:
            bar_count = count['count']
        else:
            bar_count = count[0] if isinstance(count, tuple) else count['COUNT(*)']

        if bar_count == 0:
            c.execute('''INSERT INTO bars (name, slug, location, total_tables)
                         VALUES (%s, %s, %s, %s)''' if USE_POSTGRES else
                      '''INSERT INTO bars (name, slug, location, total_tables)
                         VALUES (?, ?, ?, ?)''',
                      ('Demo Bar', 'demo-bar', 'San Francisco, CA', 4))
            print("✅ Created demo bar")

        conn.commit()
        print("✅ Database initialized")

# ============================================================================
# QUERY HELPERS
# ============================================================================

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query"""
    with get_db_connection() as conn:
        c = conn.cursor()

        # Convert ? to %s for PostgreSQL
        if USE_POSTGRES and params:
            query = query.replace('?', '%s')

        if params:
            c.execute(query, params)
        else:
            c.execute(query)

        if fetch_one:
            result = c.fetchone()
            return dict(result) if result else None
        elif fetch_all:
            results = c.fetchall()
            return [dict(row) for row in results]
        else:
            conn.commit()
            if USE_POSTGRES and 'INSERT' in query.upper() and 'RETURNING' not in query.upper():
                # Get last inserted ID for PostgreSQL
                c.execute("SELECT lastval()")
                return c.fetchone()['lastval']
            elif not USE_POSTGRES and 'INSERT' in query.upper():
                return c.lastrowid
            return None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_placeholder():
    """Get the correct placeholder for the database type"""
    return '%s' if USE_POSTGRES else '?'

def dict_from_row(row):
    """Convert database row to dictionary"""
    if row is None:
        return None
    return dict(row)
