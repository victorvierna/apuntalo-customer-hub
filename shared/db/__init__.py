"""Access to the SQLite database (schema in ``docs/architecture/database.md``).

All SQL lives in this package, so the rest of the system never writes queries
and a future move to PostgreSQL only touches these files.
"""
