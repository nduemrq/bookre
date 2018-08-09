import os, requests

from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

#IntegrityError
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    if session.get("user_id") is None:
        session["user_id"] = []
    return render_template("index.html", user_id = session["user_id"])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")

        if len(name)<3 or not name:
            return render_template("register.html", message="Invalid name", alert="alert-danger")
        if len(password)<3 or not password:
            return render_template("register.html", message="Invalid password", alert="alert-danger")
        
        try:
            db.execute("INSERT INTO member (name, password) VALUES (:name, :password)", {"name": name, "password": password})
        except IntegrityError:
            db.commit()
            return render_template("register.html", message="Login alerdy exists", alert="alert-danger")
        
        db.commit()
        return render_template("register.html", message=f"Success registrated {name}", alert="alert-success")
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        
        if len(name)<3 or not name:
            return render_template("login.html", message="Invalid name", alert="alert-danger")
        if len(password)<3 or not password:
            return render_template("login.html", message="Invalid password", alert="alert-danger")
        
        session["user_id"] = db.execute("SELECT id FROM member WHERE name = :name AND password = :password", {"name": name, "password": password}).fetchone()
        
        if not session["user_id"]:
            return render_template("login.html", message="Invalid name or password", alert="alert-danger")
        else:
            return redirect(url_for('index'))
        
    return render_template("login.html")


@app.route("/logout")
def logout():
    session["user_id"] = None
    return redirect(url_for('index'))


@app.route("/allBook")
def allBook():
    pass


@app.route("/search", methods=["POST"])
def search():
    if request.method == "POST":
        search = request.form. get("search")        
        if search is None or search is '':
            return render_template("index.html", searchMessage = "Do you want search nothing?", user_id = session["user_id"])
        
        try:
            find = db.execute("SELECT * FROM book WHERE title ILIKE :search", {"search": "%"+search+"%"}).fetchall()
            find += db.execute("SELECT * FROM book WHERE author ILIKE :search", {"search": "%"+search+"%"}).fetchall()
            find += db.execute("SELECT * FROM book WHERE isbn ILIKE :search", {"search": "%"+search+"%"}).fetchall()         
        except e:
            return render_template("index.html", searchMessage = "Somthing gone wrong with Data Base.", user_id = session["user_id"])
        if find == []:
            return render_template("index.html", searchMessage = "Nothing found.", user_id = session["user_id"])    

        return render_template("index.html", search = search, find=find, findNumber = len(find), user_id = session["user_id"])

    
@app.route("/book/<string:book_id>", methods=["GET", "POST"])
def book(book_id):
    
    # dont show form when user have added review
    sessionReview = db.execute("SELECT * FROM review WHERE id_member = :user_id AND id_book = :book_id", {"user_id": session["user_id"][0], "book_id": book_id}).fetchone()
    
    # query db for display book details
    bookDetails = db.execute("SELECT * FROM book WHERE id = :book_id", {"book_id": book_id}).fetchone()
    
    # request for external API
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "bLUyK5Gd4FyCGGUP24pLJA", "isbns": bookDetails[1]})
    
    if res.status_code != 200:
        raise Exception('ERROR: API request unsuccessful')
        
    data = res.json()
    
    # query db for display all review
    reviewAll = db.execute("SELECT review, score, name FROM review JOIN member ON member.id = review.id_member WHERE id_book = :book_id", {"book_id": book_id}).fetchall()
    
    # insert into db new review
    if request.method == "POST":
        rate = request.form.get("rate")
        review = request.form.get("review")
        
        sessionReview = db.execute("INSERT INTO review (review, score, id_member, id_book) VALUES (:review, :score, :id_member, :id_book)", {"review": review, "score": int(rate), "id_member": session["user_id"][0], "id_book": int(book_id)})
        db.commit()
        
        return redirect(url_for('book', book_id=book_id))
    
    return render_template("index.html", book_id = book_id, sessionReview = sessionReview, bookDetails = bookDetails, res = data, reviewAll = reviewAll, user_id = session["user_id"])
