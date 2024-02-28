from flask import Flask, render_template, flash, request, url_for, redirect, session
import os
import string
import secrets
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, BLOB, DateTime
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import bcrypt
import re

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
    email = Column(String(200), nullable=False, unique=True)
    username = Column(String(200), primary_key=True, nullable=False)
    pw_hash = Column(BLOB(), nullable=False)
    
class Posts(database.Model):
    id = Column(String(200), primary_key=True, nullable=False)
    summary = Column(String(200), nullable=False)
    content = Column(String(200), nullable=False)
    space = Column(String(200), nullable=False)
    date = Column(DateTime(200), nullable=False)
    username = Column(String(200), nullable=False)
    views = Column(Integer(), nullable=False)
    likes = Column(Integer(), nullable=False)
    dislikes = Column(Integer(), nullable=False)

#Form classes
class SignUpForm(FlaskForm):
    email = StringField('Enter your email', validators=[DataRequired()])#, Email()])
    username = StringField('Enter your username', validators=[DataRequired(), Length(2, 100)])
    pw = StringField('Enter your password',  validators=[DataRequired(), Length(8, 100)])
    confirm_pw = StringField('Confirm password', validators=[DataRequired()])#EqualTo(pw.name)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Enter your username', validators=[DataRequired()])
    pw = StringField('Enter your password',  validators=[DataRequired(), Length(8, 100)])
    submit = SubmitField('Login') 

class UserForm(FlaskForm):
    new_email = StringField('Email', validators=[DataRequired()])#, Email()])
    new_username = StringField('Username', validators=[DataRequired()])
    new_pw = StringField('Password',  validators=[DataRequired(), Length(8, 100)])
    old_pw = StringField('Old password', validators=[DataRequired()])
    submit = SubmitField('Change') 
    delete = SubmitField('Delete Account') 
    cancel = SubmitField('Cancel')

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
    form = SignUpForm()
    session["username"] = None

    if form.validate_on_submit():
        pw_confirmed = (form.pw.data == form.confirm_pw.data)
        username_valid = (','  not in form.username.data)
        username_unique = (not sql_session.query(Credentials).filter(
            Credentials.username == form.username.data
        ).first())
        email_unique = (not sql_session.query(Credentials).filter(
            Credentials.email == form.email.data
        ).first())
        if not pw_confirmed:
            flash('Passwords do not match', 'error')
        elif not username_valid:
            flash(f"Invalid letter ',' in username", 'error')
        elif not username_unique:
            flash(f'Username "{form.username.data}" is unavailable', 'error')
        elif not email_unique:
            flash(f'Provided email already in use', 'error')
        else:
            #Add a credential record
            pw_hash = bcrypt.hashpw(form.pw.data.encode(), salt=bcrypt.gensalt())
            record = Credentials(
                email=form.email.data,
                username=form.username.data, pw_hash=pw_hash
            )
            sql_session.add(record)
            #Commit
            sql_session.commit()
            return redirect(url_for('login', username=session["username"]))

    return render_template('signup.html', form=form, username=session["username"])

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = None
    pw = None
    login_success = False
    form = LoginForm()
    session["username"] = None

    #Validate the form and set the variables to its values if valid
    if form.validate_on_submit():
        username = form.username.data
        pw = form.pw.data
        record = sql_session.query(Credentials).filter(Credentials.username == username).first()
        pw_hash = record.pw_hash if record else None
        login_success = (pw_hash and bcrypt.checkpw(pw.encode(), pw_hash))
        if login_success:
            session["username"] = username
            return redirect(url_for('user_home', username=username))
        else:
            flash('Incorrect Username or Password', category='error')

    return render_template('login.html', form=form, username=session["username"])

#Dynamic pages
# Search results
@app.route("/search", methods=['POST'])
def search():
    if 'username' not in session:
        session['username'] = None

    #If the query is empty, send them to an explore page
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
        keywords[-1] in re.split(pattern, str(Posts.content))
    )
    for i in range(len(keywords)-2, -1, -1):
        post_results = post_results.filter(keywords[i] in Posts.content)

    #Return a search page with post and space objects
    posts = post_results.all()
    spaces = {post.space for post in posts}
    return render_template("search_results.html", posts=posts, spaces=spaces, username=session["username"])


# Exploration page
@app.route('/explore')
def explore():
    if 'username' not in session:
        session['username'] = None

    posts = sql_session.query(Posts).all()
    spaces = {post.space for post in posts}
    return render_template('explore.html', posts=posts, spaces=spaces, username=session["username"])

# User pages
@app.route('/users/<username>')
def user_home(username):
    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    posts = sql_session.query(Posts).all()
    spaces = {post.space for post in posts}
    return render_template('user_home.html', username=username, posts=posts, spaces=spaces, authenticated=True)

@app.route('/users/<username>/account', methods=['GET', 'POST'])
def account(username):
    if "username" not in session or session["username"] != username:
        return redirect(url_for('login'))
    
    form = UserForm()
    cred_query = sql_session.query(Credentials).filter(Credentials.username == username)
    user = cred_query.first()
    form.new_email.data = user.email
    form.new_username.data = username

    if form.validate_on_submit():
        if form.delete.data:
            sql_session.delete(sql_session.query(Credentials).filter(Credentials.username == username).first())
            for post in sql_session.query(Posts).filter(Posts.username == username):
                sql_session.delete(post)
            return redirect(url_for('home'))

        if form.cancel.data:
            return render_template('account.html', 
                                   username=session["username"], form=form, changing_creds=False,
                                   authenticated=True)

        if not form.old_pw.data \
        and (form.new_email.data or form.new_username.data or form.new_pw.data):
            return render_template('account.html', 
                                   username=username, form=form, changing_creds=True,
                                   authenticated=True)

        old_pw_correct = bcrypt.checkpw(form.old_pw.data.encode(), user.pw_hash)

        username_unique = (user.username == form.new_username.data) \
        or (not sql_session.query(Credentials).filter(
            Credentials.username == form.new_username.data
        ).first())

        email_unique = (user.email == form.new_email.data) \
        or (not sql_session.query(Credentials).filter(
            Credentials.email == form.new_email.data
        ).first())

        if not old_pw_correct:
            flash('Passwords do not match', 'error')
        elif not username_unique:
            flash(f'Username "{form.new_username.data}" is unavailable', 'error')
        elif not email_unique:
            flash(f'Provided email already in use', 'error')

        if old_pw_correct and username_unique and email_unique:
            update_record = dict()
            if form.new_username.data != user.username:
                update_record[user.username] = form.new_username.data,
                #Update other tables using the new username
                sql_session.query(Posts).filter(Posts.username == user.username).update(update_record)
            if form.new_email.data != user.email:
                update_record[user.email] = form.new_email.data
            if form.new_pw.data:
                new_pw_hash = bcrypt.hashpw(form.new_pw.data.encode(), bcrypt.gensalt())
                update_record[user.pw_hash] = new_pw_hash

            cred_query.update(update_record)
            sql_session.commit()
            return redirect(url_for('account', username=username))
        else:
            return redirect(url_for('account', username=username))
    
    return render_template('account.html', username=username, form=form, changing_creds=False, 
                           authenticated=True)

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