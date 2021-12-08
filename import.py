import os
from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import csv
import requests

app = Flask(__name__)

# Set up database
engine = create_engine("mysql+pymysql://root:tushar@localhost:3306/movie_rec")
db = scoped_session(sessionmaker(bind=engine))

api_key = "877ae90400e9739d4b1c98174be39af4"

def main():
    create_tables()
    for i in range(2, 2000):
        
        try:
            title, year, author, rating, count = get_movie_key(i)
            print(f"Adding {title.lower().strip()}")
            db.execute("INSERT INTO movies(movieid, title, author, year, rating_count, average_score) VALUES(:movieid, :title, :author, :year, :rating_count, :average_score)",{"movieid":i, "title":title.lower().strip(), "author":author.lower().strip(), "year":int(year), "rating_count":int(count), "average_score":float(rating)})
        except:
            print(i, "Error Occured")
    db.commit()

def create_tables():
    print("Creating Tables")
    db.execute("CREATE TABLE IF NOT EXISTS movies(movieid VARCHAR(255), title VARCHAR(255), author VARCHAR(255), year INTEGER, rating_count INTEGER, average_score FLOAT, PRIMARY KEY(movieid));")
    db.commit()

def showtables():
    movies = db.execute("SELECT * FROM movies").fetchall()
    for movie in movies:
        print(f"{movie.title} {movie.author} {movie.year}")


def get_movie_key(movie_id):
    #https://api.themoviedb.org/3/movie/550?api_key=877ae90400e9739d4b1c98174be39af4
    
    res = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}")
    details = res.json()
    
    print(details["original_title"], details["release_date"][:4], details["production_companies"][0]["name"], details["vote_average"], details["vote_count"])

    return (details["original_title"], details["release_date"][:4], details["production_companies"][0]["name"], details["vote_average"], details["vote_count"])

if(__name__ == "__main__"):
    main()
