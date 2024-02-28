import sqlite3
import os

parent_parent_dir = os.path.split(os.path.split(__file__)[0])[0]
db_path = os.path.join(parent_parent_dir, 'db', 'user_data.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS Credentials')
cursor.execute('DROP TABLE IF EXISTS Posts')
cursor.execute('DROP TABLE IF EXISTS Activity')
cursor.execute('DROP TABLE IF EXISTS Spaces')
cursor.execute('CREATE TABLE Credentials(username TEXT PRIMARY KEY, email TEXT, pw_hash BLOB)')
cursor.execute(
    """
    CREATE TABLE Posts
    (id TEXT PRIMARY KEY, summary TEXT, content TEXT, 
    space TEXT, date TEXT, username TEXT,
    views INTEGER, likes INTEGER, dislikes INTEGER)
    """
)
conn.commit()