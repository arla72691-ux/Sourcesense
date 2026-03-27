# db.py
import sqlite3
from contextlib import contextmanager

# This context manager will be used by all agents to interact with the database.
# It ensures that connections are handled properly and transactions are committed
# or rolled back as needed.

def next_id(cursor, table: str, pk_col: str, prefix: str) -> str:
    """
    Generate the next sequential VARCHAR primary key for a table.
    IDs follow the pattern '{prefix}-{seq:04d}', e.g. 'EVT-0042'.
    Uses COUNT(*)+1 — safe since rows are never deleted in this system.
    """
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    seq = cursor.fetchone()[0] + 1
    return f"{prefix}-{seq:04d}"


@contextmanager
def get_db(db_path: str):
    """Provides a database connection context manager."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # Allows accessing columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        # In a real application, you'd log this error more robustly.
        print(f"Database error: {e}")
        raise
    finally:
        conn.close()
