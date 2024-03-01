from flask import Flask, render_template, flash, request, url_for, redirect, session
import os
import string
import secrets
from datetime import datetime
import bcrypt
import re
import random
import uuid
import typing as tp
import sqlite3

proj_dir = os.path.split(os.path.split(__file__)[0])[0]
static_dir = os.path.join(proj_dir, 'static')
templates_dir = os.path.join(proj_dir, 'templates')
db_path = os.path.join(proj_dir, 'db', 'user_data.sqlite3')

app = Flask(__name__, static_folder=static_dir, template_folder=templates_dir)
app.config['SECRET_KEY'] = ''.join(
    secrets.choice(string.ascii_letters + string.digits) 
    for _ in range(32)
)

global_resources = dict()


#Utility
def get_db()->tuple[sqlite3.Connection, sqlite3.Cursor, list[str], list[str]]:
    if "conn" not in global_resources:
        global_resources["conn"] = sqlite3.connect(db_path, check_same_thread=False)
    if "cursor" not in global_resources:
        global_resources["cursor"] = cursor = global_resources["conn"].cursor()
    if "Users_cols" not in global_resources:
        global_resources["Users_cols"] = [
            record[1] for record in
            cursor.execute("PRAGMA table_info(Users)").fetchall()
        ]
    if "Posts_cols" not in global_resources:
        global_resources["Posts_cols"] = [
            record[1] for record in
            cursor.execute("PRAGMA table_info(Posts)").fetchall()
        ]
    return (
        global_resources["conn"], global_resources["cursor"], 
        global_resources["Users_cols"], global_resources["Posts_cols"]
    )

def records_to_dicts(records: list[tuple], col_list: list[str])->list[dict]:
    return [
        {
            col_list[i]: record[i] 
            for i in range(len(record))
        } 
        for record in records
    ]

def get_spaces(posts: list[dict])->dict[str, dict[str, str]]:
    conn, cursor, Users_cols, Posts_cols  = get_db()

    result = dict()

    for post in posts:
        space = post["space"]
        n_posts = 0
        for _post in posts:
            _space = _post["space"]
            n_posts += (_space == space)
        result[space] = dict(summary="No summary at this time", n_posts=n_posts)

    return result

def format_posts(
    posts: list[dict]
)->list[dict[str, tp.Union[str, dict[str, tp.Union[str, int]]]]]:
    conn, cursor, Users_cols, Posts_cols  = get_db()

    formatted = []
    for i in range(len(posts)):
        post = posts[i]
        username = post.pop("username")
        date_and_time = post.pop("date_and_time")
        date, time = date_and_time.split()
        post["date"], post["time"] = date, time
        post["user"] = dict(
            name=username,
            points=(
                cursor.execute(
                    "SELECT points FROM Users WHERE username = ?", 
                    (username,)
                ).fetchone()[0]
            )
        )
        formatted.append(post)
    return formatted

#Static site pages
# Meta
@app.route('/')
@app.route('/home')
@app.route('/home/')
def home():
    if 'username' not in session:
        session['username'] = None
    return render_template('index.html', username=session["username"])

@app.route('/about')
@app.route('/about/')
def about():
    if 'username' not in session:
        session['username'] = None

    return render_template('about.html', username=session["username"])

# Authentication
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    conn, cursor, Users_cols, Posts_cols  = get_db()

    if request.method == "POST":
        cursor = conn.cursor()
        username = request.form["username"]
        email = request.form["email"]
        pw = request.form["password"]
        confirm_pw = request.form["confirm_password"]

        pw_confirmed = (pw == confirm_pw)
        username_valid = (','  not in username)
        username_unique = (not cursor.execute(
            "SELECT 1 FROM Users WHERE username = ?", 
            (username,)
        ).fetchall())
        email_unique = (not cursor.execute(
            "SELECT 1 FROM Users WHERE email = ?", 
            (email,)
        ).fetchall())

        if not pw_confirmed:
            flash('Passwords do not match', 'error')
        elif not username_valid:
            flash(f"Invalid letter ',' in username", 'error')
        elif not username_unique:
            flash(f'Username is unavailable', 'error')
        elif not email_unique:
            flash(f'Provided email already in use', 'error')
        else:
            pw_hash = bcrypt.hashpw(pw.encode(), salt=bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO Users VALUES(?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    username,
                    email,
                    pw_hash.decode(),
                    0
                )
            )
            conn.commit()

            return redirect(url_for('login'))

    return render_template('signup.html', username=session["username"])

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn, cursor, Users_cols, Posts_cols  = get_db()

    username = None
    pw = None
    login_success = False
    session["username"] = None

    if request.method == "POST":
        username = request.form["username"]
        pw = request.form["password"]
        try:
            pw_hash = cursor.execute(
                "SELECT pw_hash FROM Users WHERE username = ?",
                (username,)
            ).fetchone()[0]
            login_success = (pw_hash and bcrypt.checkpw(pw.encode(), pw_hash.encode()))
            if login_success:
                session["username"] = username
                return redirect(url_for('user_home', username=session["username"]))
        except Exception:
            flash('Incorrect Username or Password', category='error')

    return render_template('login.html', username=session["username"])

#Dynamic pages
# Search results
@app.route("/search", methods=['GET', 'POST'])
def search():
    return redirect(url_for("explore"))

    conn, cursor, Users_cols, Posts_cols  = get_db()

    if 'username' not in session:
        session['username'] = None

    #Redirect GETs to explore
    if request.method == "GET":
        return redirect(url_for("explore"))

    #If the query is empty, Redirect to explore
    query = request.form["search"]
    if not len(query):
        return redirect(url_for("explore"))
    
    #Split the query into keywords 
    # while ignoring certain words like 'the' or 'that' if possible
    grammatical_tokens = {
        r",", r".", r"!", r"\?", r":", r";", r"'", r'"', r"\(", r"\)", 
        r"\[", r"\]", r"\{", r"\}", r"<", r">", r"/"
    }
    pattern = f"[\s|{'|'.join(grammatical_tokens)}]+"
    stopwords = {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
        "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
        "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
        "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until",
        "while", "of", "at", "by", "for", "with", "about", "against", "between", "into",
        "through", "during", "before", "after", "above", "below", "to", "from", "up", "down",
        "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
    }
    keywords = [word for word in re.split(pattern, query) if word not in stopwords]
    if not len(keywords):
        keywords = query.split()

    #Recursively shrink the pool of results by 
    # filtering the previous results on the -nth keyword
    cond = " OR ".join([f"{col} LIKE ?" for col in Posts_cols])
    sql_query =(
        f"SELECT * FROM Posts WHERE ({cond})\n" 
        + f"AND ({cond})\n"*(len(keywords) - 1)
    )
    args = []
    for i in range(len(keywords)-1, -1, -1):
        regex = f"%{keywords[i]}%"
        for _ in range(8):
            args.append(regex)

    post_results = cursor.execute(sql_query, args).fetchall()

    #Return a search page with post and space objects
    posts = format_posts(post_results)
    spaces = get_spaces(posts)
    return render_template("search_results.html", posts=posts, 
                           spaces=spaces, username=session["username"])


# Exploration page
@app.route('/explore')
def explore():
    conn, cursor, Users_cols, Posts_cols  = get_db()

    if 'username' not in session:
        session['username'] = None

    posts = records_to_dicts(cursor.execute("SELECT * FROM Posts").fetchall(), Posts_cols)
    print(posts)
    posts = format_posts(random.sample(posts, min([100, len(posts)])))
    spaces = get_spaces(posts)
    return render_template('explore.html', posts=posts, 
                           spaces=spaces, username=session["username"])

# User pages
@app.route('/users/<username>')
def user_home(username):
    conn, cursor, Users_cols, Posts_cols  = get_db()

    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    posts = records_to_dicts(cursor.execute("SELECT * FROM Posts").fetchall(), Posts_cols)
    posts = format_posts(random.sample(posts, min([100, len(posts)])))
    spaces = get_spaces(posts)
    return render_template('user_home.html', username=username, posts=posts, spaces=spaces)

@app.route('/users/<username>/new_post', methods=["GET", "POST"])
def new_post(username):
    conn, cursor, Users_cols, Posts_cols  = get_db()

    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        id = uuid.uuid4().hex
        date_and_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = request.form["title"]
        content = request.form["content"]
        space = '_'.join(request.form["space"].split())

        cursor.execute(
            f"INSERT INTO Posts VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (id, username, date_and_time, "", title, content, space, 0)   
        )
        conn.commit()

        return redirect(url_for("user_home", username=username))
    else:
        return render_template('new_post.html', username=session["username"])
    
@app.route("/users/<username>/post_service/disposition", methods=["POST"])
def post_disposition(username):
    conn, cursor, Users_cols, Posts_cols  = get_db()

    data = request.get_json()
    post_id = data["postId"]
    disposition = int(data["disposition"])
    
    cursor.execute(
        "UPDATE Users SET points = points + ? WHERE username = ?",
        (disposition, username)
    )
    cursor.execute(
        "UPDATE Users SET points = points + ? WHERE id = ?",
        (disposition, post_id)
    )
    conn.commit()


    user_pts = cursor.execute(
        "SELECT points FROM Users WHERE username = ?", 
        (username,)
    ).fetchone()[0]
    post_pts = cursor.execute(
        "SELECT points FROM Posts WHERE id = ?", 
        (post_id,)
    ).fetchone()[0]
    return {"user_points": user_pts, "post_points": post_pts}

@app.route('/users/<username>/account', methods=['GET', 'POST'])
def account(username):
    conn, cursor, Users_cols, Posts_cols  = get_db()

    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    if request.method == "GET":
        return render_template(
            'account.html', username=session["username"], email=user_record.email, 
        )
    elif request.form["btn"] == "delete":
        cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
        cursor.execute("DELETE FROM Posts WHERE username = ?", (username,))
        session["username"] = None
        conn.commit()
        return redirect(url_for('home'))
    else:
        user_record = records_to_dicts(
            cursor.execute(
                "SELECT * FROM Users WHERE username = ?", 
                (username,)
            ).fetchall(),
            Users_cols
        )[0]

        new_username = request.form["username"]
        new_email = request.form["email"]
        new_pw = request.form["password"]
        old_pw = request.form["old_password"]

        old_pw_correct = bcrypt.checkpw(old_pw.encode(), user_record.pw_hash.encode())
        username_unique = (username == new_username) \
        or (not cursor.execute(
            "SELECT 1 FROM Users WHERE username = ?", 
            (username,)
        ).fetchall())
        email_unique = (user_record.email == new_email) \
        or (not cursor.execute(
            "SELECT 1 FROM Users WHERE email = ?", 
            (new_email,)
        ).fetchall())

        if not old_pw_correct:
            flash('Incorrect old password', 'error')
        elif not username_unique:
            flash(f'Username is unavailable', 'error')
        elif not email_unique:
            flash(f'Provided email already in use', 'error')

        if old_pw_correct and username_unique and email_unique:
            if new_username and new_username != user_record.username:
                cursor.execute(
                    "UPDATE Users SET username = ? WHERE username = ?",
                    (new_username, username)
                )
                cursor.execute(
                    "UPDATE Users SET username = ? WHERE username = ?",
                    (new_username, username)
                )
                session["username"] = new_username
            if new_email and new_email != user_record.email:
                cursor.execute(
                    "UPDATE Users SET email = ? WHERE username = ?",
                    (new_email, username)
                )
            if new_pw and new_pw != old_pw:
                new_pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt())
                cursor.execute(
                    "UPDATE Users SET pw_hash = ? WHERE username = ?",
                    (new_pw_hash.decode(), username)
                )
            conn.commit()
                
            return redirect(url_for('account', username=session["username"]))
        else:
            return redirect(url_for('account', username=session["username"]))

#Error handlers
@app.errorhandler(404)
def page_not_found(err):
    return render_template('404.html')

@app.errorhandler(500)
def server_error(err):
    return render_template('500.html')

#Not yet implemented
if __name__ == '__main__':
    app.run(debug=True)