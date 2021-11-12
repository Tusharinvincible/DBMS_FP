import os
from flask import Flask, session, render_template, request, redirect, url_for, jsonify, abort
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
# os.getenv("DATABASE_URL")
engine = create_engine("mysql+pymysql://root:nerf@localhost:3306/book_rec")
db = scoped_session(sessionmaker(bind=engine))

def create_reviews_tables():
    db.execute("CREATE TABLE IF NOT EXISTS reviews(id INT, username VARCHAR(255), isbn VARCHAR(255), review VARCHAR(255), rating INTEGER, FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,  FOREIGN KEY (isbn) REFERENCES books(isbn) ON DELETE CASCADE)")
    db.commit()

def create_users_table():
    db.execute("CREATE TABLE IF NOT EXISTS users(id INT AUTO_INCREMENT, username VARCHAR(255), email VARCHAR(255), password VARCHAR(255), PRIMARY KEY(id))")
    db.commit()

def show_reviews_table(isbn):
    reviews = db.execute("SELECT * FROM reviews WHERE isbn=:isbn", {"isbn":isbn})
    for review in reviews:
        print(review.users, review.username, review.isbn, review.review, review.rating)

@app.route("/")
def index():
    if(session.get("user") == None):
        return redirect(url_for("login"))
    else:
        return redirect(url_for("dashboard"))

@app.route("/login")
def login():
    if(session.get("data_err") == None):
        return render_template("login.html", message = "")
    else:
        del session["data_err"]
        return render_template("login.html", message= "Incorrect Username or Password")

@app.route("/dashboard", methods = ["POST","GET"])
def dashboard():
    if(request.method == "POST"):
        if("loginsubmit" in request.form):
            create_users_table()
            user = db.execute("SELECT * FROM users WHERE username = :username",{"username": request.form.get("username")}).fetchone()

            if(user != None):
                if(user.password == request.form.get("password")):
                    session["user"] = user
                    return render_template("index.html", user = user)
                else:
                    session["data_err"] = "Incorrect Password"
                    return redirect(url_for("login"))
            else:
                session["data_err"] = "Incorrect Username"
                return redirect(url_for("login"))

        else:
            create_users_table()
            user_exists = db.execute("SELECT * FROM users WHERE username=:username", {"username":request.form.get("username")}).fetchone()
            if(user_exists != None):
                return render_template("login.html", message = "A user with that username Already exists")
            db.execute("INSERT INTO users (username, email, password) VALUES (:username, :email, :password)", {"username":request.form.get("username"),"email":request.form.get("email"), "password":request.form.get("password")})
            db.commit()
            user = db.execute("SELECT * FROM users WHERE username = :username",{"username": request.form.get("username")}).fetchone()
            session["user"] = user
            return render_template("index.html", user = user)
    else:
        if(session.get("user") != None):
            return render_template("index.html", user = session["user"])
        else:
            abort(404)


@app.route("/logout")
def logout():
    del session["user"]
    return redirect(url_for("login"))

@app.route("/search", methods = ["POST","GET"])
def search():
    if(request.method == "GET"):
        return redirect(url_for("dashboard"))
    search_query = request.form.get("search_books").lower().strip()
    books = db.execute(f"SELECT * FROM books WHERE isbn LIKE '%{search_query}%'").fetchall()
    #books = db.execute("SELECT * FROM books WHERE isbn LIKE '%:isbn%'",{"isbn": search_query}).fetchall()

    books.extend(db.execute(f"SELECT * FROM books WHERE title LIKE '%{search_query}%'").fetchall())
    #books = db.execute("SELECT * FROM books WHERE title LIKE '%:title%'",{"title": search_query}).fetchall()

    books.extend(db.execute(f"SELECT * FROM books WHERE author LIKE '%{search_query}%'").fetchall())
    #books = db.execute("SELECT * FROM books WHERE author LIKE '%:author%'",{"author": search_query}).fetchall()
    return render_template("search.html", user = session["user"], books = books)

@app.route("/book/<string:book_id>")
def book(book_id):
    create_reviews_tables()
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":book_id}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn":book_id}).fetchall()
    return render_template("book.html", user = session["user"], book = book, reviews = reviews, message = "")

@app.route("/review/<string:book_id>", methods = ["POST"])
def review(book_id):
    user_review =  request.form.get("user_review")
    user_rating = int(request.form.get("rating"))
    users =  db.execute("SELECT * FROM users").fetchall()
    book_data = db.execute("SELECT rating_count, average_score FROM books WHERE isbn = :isbn",{"isbn":book_id}).fetchone()
    rating_count = book_data[0]
    average_score = book_data[1]
    if(db.execute("SELECT * FROM reviews WHERE id = :userid AND isbn = :isbn", {"userid":session["user"].id, "isbn":book_id}).fetchone() is None):
        db.execute("INSERT INTO reviews (id, username, isbn, review, rating) VALUES (:id, :username, :isbn, :review, :rating)", {"id":session["user"].id, "username":session["user"].username, "isbn":book_id, "review":user_review, "rating": user_rating})
        db.commit()
    else:
        reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn":book_id}).fetchall()
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":book_id}).fetchone()
        return render_template("book.html", user = session["user"], book = book, reviews = reviews, message = "You have already Written a review for this book")

    total_rating = int(average_score * rating_count)
    rating_count+=1
    average_score = (total_rating + user_rating)/rating_count
    db.execute("UPDATE books SET rating_count = :rating_count, average_score = :average_score WHERE isbn = :isbn", {"rating_count":rating_count, "average_score":average_score, "isbn":book_id})
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":book_id}).fetchone()
    db.commit()
    return redirect(url_for("book", book_id = book_id))

@app.route("/api/<string:book_id>")
def get_book_api(book_id):
    # {
    # "title": "Memory",
    # "author": "Doug Lloyd",
    # "year": 2015,
    # "isbn": "1632168146",
    # "review_count": 28,
    # "average_score": 5.0
    # }
    # Required Response
    book_details = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":book_id}).fetchone()
    book_dict = {}
    book_dict["title"] = book_details.title
    book_dict["author"] = book_details.author
    book_dict["year"] = book_details.year
    book_dict["isbn"] = book_details.isbn
    book_dict["review_count"] = book_details.rating_count
    book_dict["average_score"] = book_details.average_score
    return jsonify(book_dict)
