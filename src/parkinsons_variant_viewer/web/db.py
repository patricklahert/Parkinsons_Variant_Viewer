import sqlite3
from flask import g, current_app

# Return an open database connection (cached per request)
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

# Close the database connection when the request ends 
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Initialise the database using schema.sql 
def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f: 
        db.executescript(f.read().decode('utf8'))

# Helper so loader can get DB path
def get_db_path(): 
    """
    Return the absolute path to the SQLite database file.
    """
    return current_app.config['DATABASE']
