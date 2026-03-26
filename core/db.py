# db.py
import sqlite3
from contextlib import contextmanager

# This context manager will be used by all agents to interact with the database.
# It ensures that connections are handled properly and transactions are committed
# or rolled back as needed.

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
