import argparse
import sqlite3
import bcrypt
import os

parser = argparse.ArgumentParser()
parser.add_argument('-u', required=True)
parser.add_argument('-e', required=True)
parser.add_argument('-p', required=True)
args = parser.parse_args()

if args:
    print('Adding record to credential table:')
    print(f'-username: {args.u}\n-email: {args.e}\n-password: {args.p}')
    parent_parent_dir = os.path.split(os.path.split(__file__)[0])[0]
    db_path = os.path.join(parent_parent_dir, 'db', 'user_data.sqlite3')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Credentials VALUES(?, ?, ?)', 
        (args.u, args.e, bcrypt.hashpw(args.p.encode(), bcrypt.gensalt()).decode())
    )
    conn.commit()
    print("User added")