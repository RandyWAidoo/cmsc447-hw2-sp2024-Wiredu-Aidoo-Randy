import sqlite3
import os

proj_dir = os.path.split(os.path.split(__file__)[0])[0]
db_path = os.path.join(proj_dir, 'db', 'user_data.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS Credentials')
cursor.execute('DROP TABLE IF EXISTS Users')
cursor.execute('DROP TABLE IF EXISTS Posts')
cursor.execute('DROP TABLE IF EXISTS Activity')
cursor.execute('DROP TABLE IF EXISTS Spaces')

cursor.execute(
    """
    CREATE TABLE Users
    (id TEXT TEXT PRIMARY KEY, 
    username TEXT UNIQUE, email TEXT UNIQUE, 
    pw_hash TEXT, points INTEGER DEFAULT 0)
    """
)
cursor.execute(
    """
    CREATE TABLE Posts
    (id TEXT PRIMARY KEY, username TEXT, date_and_time TEXT,
    summary TEXT DEFAULT '', 
    title TEXT, content TEXT, space TEXT,
    points INTEGER DEFAULT 0)
    """
)
conn.commit()