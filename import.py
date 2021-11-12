import os
from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import csv
import requests

app = Flask(__name__)

# postgresql://postgres:nerf123@localhost:5432/book_rec
# mysql+pymysql://root:nerf@localhost:3306/book_rec

# Set up database
engine = create_engine("mysql+pymysql://root:nerf@localhost:3306/book_rec")
db = scoped_session(sessionmaker(bind=engine))

api_key = "AIzaSyDVg6bM4M57n49SZ5bHEeaZhoBiXJZMm5Q"

def main():
    create_tables()
    with open("books.csv", "r") as books:
        reader = csv.reader(books)
        next(reader)
        for isbn, title, author, year in reader:
            print(f"Adding {title.lower().strip()}")
            try:
                count, rating = get_book_key(isbn)
                db.execute("INSERT INTO books(isbn, title, author, year, rating_count, average_score) VALUES(:isbn, :title, :author, :year, :rating_count, :average_score)",{"isbn":isbn, "title":title.lower().strip(), "author":author.lower().strip(), "year":int(year), "rating_count":int(count), "average_score":float(rating)})
            except:
                print("Error Occured")
    db.commit()

def create_tables():
    print("Creating Tables")
    db.execute("CREATE TABLE IF NOT EXISTS books(isbn VARCHAR(255), title VARCHAR(255), author VARCHAR(255), year INTEGER, rating_count INTEGER, average_score FLOAT, PRIMARY KEY(isbn));")
    db.commit()

def showtables():
    books = db.execute("SELECT * FROM books").fetchall()
    for book in books:
        print(f"{book.isbn} {book.title} {book.author} {book.year}")


def get_book_key(isbn):
    #https://www.googleapis.com/books/v1/volumes?q=isbn:9780552152679&key?=AIzaSyDVg6bM4M57n49SZ5bHEeaZhoBiXJZMm5Q
    res = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key?={api_key}")
    details = res.json()
    print(details)
    print(details["items"][0]["volumeInfo"]["ratingsCount"], details["items"][0]["volumeInfo"]["averageRating"])

    return (details["items"][0]["volumeInfo"]["ratingsCount"], details["items"][0]["volumeInfo"]["averageRating"])

if(__name__ == "__main__"):
    main()
