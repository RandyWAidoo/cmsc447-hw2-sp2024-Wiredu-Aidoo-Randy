from sys import argv
import sqlite3
import bcrypt
import os

argv = argv[1:]
if argv:
    print(f'Deleting user(s) {argv} from credential table...')
    parent_parent_dir = os.path.split(os.path.split(__file__)[0])[0]
    db_path = os.path.join(parent_parent_dir, 'db', 'user_data.sqlite3')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        f'DELETE FROM Credentials WHERE username IN ({", ".join("?"*len(argv))})',
        [user for user in argv]
    )
    conn.commit()
    print("User(s) deleted")