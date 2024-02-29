from flask import Flask, render_template, flash, request, url_for, redirect, session
import os
import string
import secrets
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (create_engine, MetaData, Table, 
                        Column, Integer, String, BLOB, DateTime, 
                        update)
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import bcrypt
import re
import random
import uuid

app = Flask(__name__, static_folder="../static", template_folder="../templates")
app.config['SECRET_KEY'] = ''.join(
    secrets.choice(string.ascii_letters + string.digits) 
    for _ in range(32)
)
parent_parent_dir = os.path.split(os.path.split(__file__)[0])[0]
db_path = os.path.join(parent_parent_dir, 'db', 'user_data.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
sql_session = sessionmaker(bind=engine)()
database = SQLAlchemy(app)

proj_dir = os.sep.join(os.path.normpath(__file__).split(os.sep)[:-1])
template_dir = os.path.join(proj_dir, 'templates')

#Table classes
class Credentials(database.Model):
    username = Column(String(200), primary_key=True, nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    pw_hash = Column(String(), nullable=False)
    
class Posts(database.Model):
    id = Column(String(200), primary_key=True, nullable=False)
    username = Column(String(200), nullable=False)
    date_and_time = Column(String(200), nullable=False)
    summary = Column(String(200), nullable=False, default="")
    title = Column(String(200), nullable=False)
    content = Column(String(), nullable=False)
    space = Column(String(200), nullable=False)
    views = Column(Integer(), nullable=False, default=0)
    likes = Column(Integer(), nullable=False, default=0)
    dislikes = Column(Integer(), nullable=False, default=0)

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
    session["username"] = None

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        pw = request.form["password"]
        confirm_pw = request.form["confirm_password"]

        pw_confirmed = (pw == confirm_pw)
        username_valid = (','  not in username)
        username_unique = (not sql_session.query(Credentials).filter(
            Credentials.username == username
        ).first())
        email_unique = (not sql_session.query(Credentials).filter(
            Credentials.email == email
        ).first())

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
            record = Credentials(
                email=email,
                username=username, pw_hash=pw_hash.decode()
            )

            sql_session.add(record)
            sql_session.commit()

            return redirect(url_for('login'))

    return render_template('signup.html', username=session["username"])

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = None
    pw = None
    login_success = False
    session["username"] = None

    if request.method == "POST":
        username = request.form["username"]
        pw = request.form["password"]
        record = sql_session.query(Credentials).filter(Credentials.username == username).first()
        pw_hash = record.pw_hash if record else None
        login_success = (pw_hash and bcrypt.checkpw(pw.encode(), pw_hash.encode()))
        if login_success:
            session["username"] = username
            return redirect(url_for('user_home', username=session["username"]))
        else:
            flash('Incorrect Username or Password', category='error')

    return render_template('login.html', username=session["username"])

#Dynamic pages
# Search results
@app.route("/search", methods=['GET', 'POST'])
def search():
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
        ",", ".", "!", "?", ":", ";", "'", "\"", "\(", "\)", 
        "[", "]", "{", "}", "<", ">", "/", "\\"
    }
    pattern = f"[\s{''.join(grammatical_tokens)}]+"
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
    post_results = sql_session.query(Posts).filter(
        keywords[-1] in re.split(
            pattern, 
            ' '.join([
                str(Posts.username), 
                str(Posts.title), 
                str(Posts.content), 
                str(Posts.space)
            ])
        )
    )
    for i in range(len(keywords)-2, -1, -1):
        post_results = post_results.filter(keywords[i] in Posts.fill_content)

    #Return a search page with post and space objects
    posts = post_results.all()
    spaces = {post.space for post in posts}
    return render_template("search_results.html", posts=posts, 
                           spaces=spaces, username=session["username"])


# Exploration page
@app.route('/explore')
def explore():
    if 'username' not in session:
        session['username'] = None

    posts = sql_session.query(Posts).all()
    posts = random.sample(posts, min([100, len(posts)]))
    spaces = {
        post.space: dict( 
            summary="No summary at this time",
            n_posts=len([_post for _post in posts if _post.space == post.space])
        ) 
        for post in posts
    }
    return render_template('explore.html', posts=posts, 
                           spaces=spaces, username=session["username"])

# User pages
@app.route('/users/<username>')
def user_home(username):
    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    posts = sql_session.query(Posts).all()
    posts = random.sample(posts, min([100, len(posts)]))
    spaces = {
        post.space: dict( 
            summary="No summary at this time",
            n_posts=len([_post for _post in posts if _post.space == post.space])
        ) 
        for post in posts
    }
    return render_template('user_home.html', username=username, posts=posts, spaces=spaces)

@app.route('/users/<username>/new_post', methods=["GET", "POST"])
def new_post(username):
    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        id = uuid.uuid4().hex
        date_and_time = datetime.now().strftime("%Y-%m-%d %h:%M:%S")
        title = request.form["title"]
        content = request.form["content"]
        space = ''.join(request.form["space"].split())

        sql_session.add(Posts(
            id=id, username=username, 
            date_and_time=date_and_time, 
            title=title, content=content, space=space
        ))
        sql_session.commit()

        return redirect(url_for("user_home", username=username))
    else:
        return render_template('new_post.html', username=username)

@app.route('/users/<username>/account', methods=['GET', 'POST'])
def account(username):
    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    cred_query = sql_session.query(Credentials).filter(Credentials.username == username)
    user = cred_query.first()
    
    if request.method == "GET":
        return render_template(
            'account.html', username=session["username"], email=user.email, 
        )
    elif request.form["btn"] == "delete":
        sql_session.delete(user)
        for post in sql_session.query(Posts).filter(Posts.username == username):
            sql_session.delete(post)
        session["username"] = None
        sql_session.commit()
        return redirect(url_for('home'))
    else:
        new_username = request.form["username"]
        new_email = request.form["email"]
        new_pw = request.form["password"]
        old_pw = request.form["old_password"]

        old_pw_correct = bcrypt.checkpw(old_pw.encode(), user.pw_hash.encode())

        username_unique = (user.username == new_username) \
        or (not sql_session.query(Credentials).filter(
            Credentials.username == new_username
        ).first())

        email_unique = (user.email == new_email) \
        or (not sql_session.query(Credentials).filter(
            Credentials.email == new_email
        ).first())

        if not old_pw_correct:
            flash('Incorrect old password', 'error')
        elif not username_unique:
            flash(f'Username is unavailable', 'error')
        elif not email_unique:
            flash(f'Provided email already in use', 'error')

        if old_pw_correct and username_unique and email_unique:
            update_record = dict()

            if new_username and new_username != user.username:
                update_record["username"] = new_username
                user_posts = sql_session.query(Posts).filter(Posts.username == user.username)
                user_posts.update({"username": new_username})

                session["username"] = new_username

            if new_email and new_email != user.email:
                update_record["email"] = new_email

            if new_pw and new_pw != old_pw:
                new_pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt())
                update_record["pw_hash"] = new_pw_hash.decode()
                
            cred_query.update(update_record)
            sql_session.commit()
                
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