"""
Database connection manager and query execution layer.
Provides unified interface across SQLite (local development) and PostgreSQL (cloud).
"""
import os
import sqlite3
from contextlib import contextmanager
from config import Config

# Optional PostgreSQL driver support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False


def dict_factory(cursor, row):
    """Convert SQLite row to dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def get_db_connection():
    """Context manager for obtaining a database connection."""
    if Config.DB_ENGINE == "postgresql" and PG_AVAILABLE:
        if Config.DATABASE_URL:
            conn = psycopg2.connect(Config.DATABASE_URL)
        else:
            conn = psycopg2.connect(
                host=Config.PG_HOST,
                port=Config.PG_PORT,
                dbname=Config.PG_DATABASE,
                user=Config.PG_USER,
                password=Config.PG_PASSWORD
            )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        # Default SQLite (Optimized for zero-latency localhost performance)
        os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_PATH, timeout=20.0)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def query_db(query, args=(), one=False):
    """Execute a SELECT query and return list of dictionaries or single row."""
    with get_db_connection() as conn:
        if Config.DB_ENGINE == "postgresql" and PG_AVAILABLE:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query.replace("?", "%s"), args)
            rv = cursor.fetchall()
            cursor.close()
            return (rv[0] if rv else None) if one else rv
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            rv = cur.fetchall()
            cur.close()
            return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    """Execute an INSERT, UPDATE, or DELETE query and return lastrowid / rowcount."""
    with get_db_connection() as conn:
        if Config.DB_ENGINE == "postgresql" and PG_AVAILABLE:
            cursor = conn.cursor()
            # If INSERT and needs returned id:
            pg_query = query.replace("?", "%s")
            cursor.execute(pg_query, args)
            rowcount = cursor.rowcount
            cursor.close()
            return rowcount
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            last_id = cur.lastrowid
            rowcount = cur.rowcount
            cur.close()
            return last_id or rowcount


def init_db():
    """Initialize database tables using schema."""
    with get_db_connection() as conn:
        if Config.DB_ENGINE == "postgresql" and PG_AVAILABLE:
            schema_file = os.path.join(Config.BASE_DIR, "database", "schema_postgresql.sql")
        else:
            schema_file = os.path.join(Config.BASE_DIR, "database", "schema_sqlite.sql")
            
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        cur = conn.cursor()
        if Config.DB_ENGINE == "postgresql" and PG_AVAILABLE:
            cur.execute(schema_sql)
        else:
            cur.executescript(schema_sql)
        cur.close()
