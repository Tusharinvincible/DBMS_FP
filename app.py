import os
import hashlib
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
engine = create_engine("mysql+pymysql://root:nerf@localhost:3306/movie_rec")
db = scoped_session(sessionmaker(bind=engine))

def create_reviews_tables():
    db.execute("CREATE TABLE IF NOT EXISTS reviews(review_id INT AUTO_INCREMENT, id INT, username VARCHAR(255), movieid VARCHAR(255), review VARCHAR(255), rating INTEGER, FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,  FOREIGN KEY (movieid) REFERENCES movies(movieid) ON DELETE CASCADE, PRIMARY KEY(review_id))")
    db.commit()

def create_users_table():
    db.execute("CREATE TABLE IF NOT EXISTS users(id INT AUTO_INCREMENT, username VARCHAR(255), email VARCHAR(255), password VARCHAR(256), PRIMARY KEY(id))")
    db.commit()

def show_reviews_table(movieid):
    reviews = db.execute("SELECT * FROM reviews WHERE movieid=:movieid", {"movieid":movieid})
    for review in reviews:
        print(review.users, review.username, review.movieid, review.review, review.rating)

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
            user = db.execute("SELECT * FROM users WHERE username = :username",{"username": request.form.get("username").strip()}).fetchone()

            if(user != None):
                if(user.password == hashlib.sha256(request.form.get("password").strip().encode()).hexdigest()):
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
            user_exists = db.execute("SELECT * FROM users WHERE username=:username", {"username":request.form.get("username").strip()}).fetchone()
            if(user_exists != None):
                return render_template("login.html", message = "A user with that username Already exists")
            if(request.form.get("username").isdigit()):
                return render_template("login.html", message = "A username should have letters in it")
            db.execute("INSERT INTO users (username, email, password) VALUES (:username, :email, :password)", {"username":request.form.get("username").strip(),"email":request.form.get("email").strip(), "password":hashlib.sha256(request.form.get("password").strip().encode()).hexdigest()})
            db.commit()
            user = db.execute("SELECT * FROM users WHERE username = :username",{"username": request.form.get("username").strip()}).fetchone()
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
    search_query = request.form.get("search_movies").lower().strip()
    movies = db.execute(f"SELECT * FROM movies WHERE movieid LIKE '%{search_query}%'").fetchall()
    #movies = db.execute("SELECT * FROM movies WHERE movieid LIKE '%:movieid%'",{"movieid": search_query}).fetchall()

    movies.extend(db.execute(f"SELECT * FROM movies WHERE title LIKE '%{search_query}%'").fetchall())
    #movies = db.execute("SELECT * FROM movies WHERE title LIKE '%:title%'",{"title": search_query}).fetchall()

    movies.extend(db.execute(f"SELECT * FROM movies WHERE author LIKE '%{search_query}%'").fetchall())
    #movies = db.execute("SELECT * FROM movies WHERE author LIKE '%:author%'",{"author": search_query}).fetchall()
    return render_template("search.html", user = session["user"], movies = movies)

@app.route("/movie/<string:movie_id>")
def movie(movie_id):
    create_reviews_tables()
    movie = db.execute("SELECT * FROM movies WHERE movieid = :movieid",{"movieid":movie_id}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE movieid = :movieid",{"movieid":movie_id}).fetchall()
    return render_template("movie.html", user = session["user"], movie = movie, reviews = reviews, message = "")

@app.route("/review/<string:movie_id>", methods = ["POST"])
def review(movie_id):
    user_review =  request.form.get("user_review").strip()
    user_rating = int(request.form.get("rating"))
    # users =  db.execute("SELECT * FROM users").fetchall()

    movie_data = db.execute("SELECT rating_count, average_score FROM movies WHERE movieid = :movieid",{"movieid":movie_id}).fetchone()
    rating_count = movie_data[0]
    average_score = movie_data[1]

    if(db.execute("SELECT * FROM reviews WHERE id = :userid AND movieid = :movieid", {"userid":session["user"].id, "movieid":movie_id}).fetchone() is None):
        db.execute("INSERT INTO reviews (id, username, movieid, review, rating) VALUES (:id, :username, :movieid, :review, :rating)", {"id":session["user"].id, "username":session["user"].username, "movieid":movie_id, "review":user_review, "rating": user_rating})
        db.commit()
    else:
        reviews = db.execute("SELECT * FROM reviews WHERE movieid = :movieid",{"movieid":movie_id}).fetchall()
        movie = db.execute("SELECT * FROM movies WHERE movieid = :movieid",{"movieid":movie_id}).fetchone()
        return render_template("movie.html", user = session["user"], movie = movie, reviews = reviews, message = "You have already Written a review for this movie")

    total_rating = int(average_score * rating_count)
    rating_count+=1
    average_score = (total_rating + user_rating)/rating_count

    db.execute("UPDATE movies SET rating_count = :rating_count, average_score = :average_score WHERE movieid = :movieid", {"rating_count":rating_count, "average_score":average_score, "movieid":movie_id})
    movie = db.execute("SELECT * FROM movies WHERE movieid = :movieid", {"movieid":movie_id}).fetchone()
    db.commit()
    return redirect(url_for("movie", movie_id = movie_id))

@app.route("/edit_post")
def edit_post():
    print(request.args.get('review_id'), request.args.get('movie_id'))
    return render_template("edit_post.html", user = session["user"], review_id = request.args.get('review_id'), movie_id = request.args.get('movie_id'), message = "")

@app.route("/review_edit", methods = ["POST"])
def review_edit():
    user_review =  request.form.get("user_review").strip()
    db.execute("UPDATE reviews SET review = :new_review WHERE review_id = :rev_id", {"new_review" : user_review,"rev_id":int(request.args.get('review_id'))})
    db.commit()

    return redirect(url_for("movie", movie_id = request.args.get('movie_id')))

@app.route("/api/<string:movie_id>")
def get_movie_api(movie_id):
    # {
    # "title": "Memory",
    # "author": "Doug Lloyd",
    # "year": 2015,
    # "movieid": "1632168146",
    # "review_count": 28,
    # "average_score": 5.0
    # }
    # Required Response
    movie_details = db.execute("SELECT * FROM movies WHERE movieid = :movieid",{"movieid":movie_id}).fetchone()
    movie_dict = {}
    movie_dict["title"] = movie_details.title
    movie_dict["author"] = movie_details.author
    movie_dict["year"] = movie_details.year
    movie_dict["movieid"] = movie_details.movieid
    movie_dict["review_count"] = movie_details.rating_count
    movie_dict["average_score"] = movie_details.average_score
    
    return jsonify(movie_dict)
