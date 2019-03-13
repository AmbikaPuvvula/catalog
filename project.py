# Imports
from flask import Flask, render_template, \
    url_for, request, redirect,\
    flash, jsonify, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import *
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import os
import random
import string
import datetime
import json
import httplib2
import requests
# Import login_required from login_decorator.py
from login_decorator import login_required

# Flask instance
app = Flask(__name__)


# GConnect CLIENT_ID

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"

# Connect to database
engine = create_engine('sqlite:///catalog.db',
                       connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine
# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Login - Create anti-forgery state token


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                                  string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# GConnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Gathers data from Google Sign In API and places
    it inside a session variable.
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is'
                                            'already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    # data = answer.json()
    data = json.loads(answer.text)
    try:
        login_session['username'] = data['name']
        login_session['picture'] = data['picture']
        login_session['email'] = data['email']
    except psycopg2.OperationalError as e:
        login_session['username'] = "Google User"
        login_session['picture'] = "http://tiny.cc/lz6m2y"
        login_session['email'] = "Google Email"

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    ' -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception as e:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session

@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    try:
        result['status'] == '200'
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = redirect(url_for('showCatalog'))
        flash("You are now logged out.")
        return response
    except Exception as e:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'+e, 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Show home page
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    genres = session.query(Genre).order_by(asc(Genre.name))
    books = session.query(Book).order_by(desc(Book.date))
    if 'username' not in login_session:
        return render_template('publiccatalog.html',
                               genres=genres, books=books)
    else:
        return render_template('catalog.html', genres=genres, books=books)


# Add a new genre
@app.route('/catalog/newgenre', methods=['GET', 'POST'])
@login_required
def newGenre():
    if request.method == 'POST':
        addingGenre = Genre(name=request.form['name'],
                            user_id=login_session['user_id'])
        session.add(addingGenre)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('newGenre.html')


# Edit a genre
@app.route('/catalog/<genre_name>/edit', methods=['GET', 'POST'])
@login_required
def editGenre(genre_name):
    genreToEdit = session.query(Genre).filter_by(name=genre_name).one()

    """Prevent logged-in user to edit other user's genre"""
    if genreToEdit.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert(' You are not authorized"\
                "to edit this genre."\
                "Please create your own " \
               "genre " \
               "in order to edit.');}</script><body onload='myFunction()'>"

    """Save edited genre to the database"""
    if request.method == 'POST':
        genreToEdit.name = request.form['name']
        session.add(genreToEdit)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('editGenre.html', genre=genreToEdit)

# Delete a genre


@app.route('/catalog/<genre_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteGenre(genre_name):
    genreToDelete = session.query(Genre).filter_by(name=genre_name).one()

    """Prevent logged-in user to delete other user's genre"""
    if genreToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
            "to delete this genre. Please create your own " \
               "genre " \
               "in order to delete.');}</script><body onload='myFunction()'>"

    """Delete genre from the database"""
    if request.method == 'POST':
        session.delete(genreToDelete)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('deleteGenre.html', genre=genreToDelete)


# Show all books in a genre
@app.route('/catalog/<genre_name>/books')
def showGenreBooks(genre_name):
    genres = session.query(Genre).order_by(asc(Genre.name))
    chosenGenre = session.query(Genre).filter_by(name=genre_name).one()
    books = session.query(Book).filter_by(
        genre_id=chosenGenre.id).order_by(asc(Book.name))
    creator = getUserInfo(chosenGenre.user_id)
    if 'username' not in login_session or\
       creator.id != login_session['user_id']:
        return render_template('publicGenreBooks.html',
                               genres=genres,
                               chosenGenre=chosenGenre,
                               books=books)
    else:
        return render_template('showGenreBooks.html',
                               genres=genres,
                               chosenGenre=chosenGenre,
                               books=books)


# Show information of a specific book
@app.route('/catalog/<genre_name>/<book_name>')
def showBook(genre_name, book_name):
    genre = session.query(Genre).filter_by(name=genre_name).one()
    book = session.query(Book).filter_by(name=book_name, genre=genre).one()
    creator = getUserInfo(book.user_id)
    if 'username' not in login_session or\
       creator.id != login_session['user_id']:
        return render_template('publicbooks.html', book=book)
    else:
        return render_template('showBook.html', book=book)


# Add a new book
@app.route('/catalog/newbook', methods=['GET', 'POST'])
@login_required
def newBook():
    genres = session.query(Genre).order_by(asc(Genre.name))
    if request.method == 'POST':
        addingBook = Book(
            name=request.form['name'],
            description=request.form['description'],
            image=request.form['image'],
            genre=session.query(
                Genre).filter_by(name=request.form['genre']).one(),
            date=datetime.datetime.now(),
            user_id=login_session['user_id'])
        session.add(addingBook)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('newBook.html',
                               genres=genres)

# Edit a book


@app.route('/catalog/<genre_name>/<book_name>/edit', methods=['GET', 'POST'])
@login_required
def editBook(genre_name, book_name):
    genres = session.query(Genre).order_by(asc(Genre.name))
    editingBookGenre = session.query(Genre).filter_by(name=genre_name).one()
    editingBook = session.query(Book).filter_by(
        name=book_name, genre=editingBookGenre).one()

    """Prevent logged-in user to edit book which belongs to other user"""
    if editingBook.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
                "to edit this book. Please create your own book " \
               "in order to edit.');}</script><body onload='myFunction()'>"

    """Save edited book to the database"""
    if request.method == 'POST':
        if request.form['name']:
            editingBook.name = request.form['name']
        if request.form['description']:
            editingBook.description = request.form['description']
        if request.form['genre']:
            editingBook.genre = session.query(Genre).filter_by(
                name=request.form['genre']).one()
        session.add(editingBook)
        session.commit()
        return redirect(url_for('showBook', genre_name=editingBookGenre.name,
                                book_name=editingBook.name))
    else:
        return render_template('editBook.html', genres=genres,
                               editingBookGenre=editingBookGenre,
                               book=editingBook)

# Delete a book


@app.route('/catalog/<genre_name>/<book_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteBook(genre_name, book_name):
    genre = session.query(Genre).filter_by(name=genre_name).one()
    deletingBook = session.query(Book).filter_by(
        name=book_name, genre=genre).one()

    """Prevent logged-in user to delete book which belongs to other user"""
    if deletingBook.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized "\
                "to delete this book. Please create your own book " \
               "in order to delete.');}</script><body onload='myFunction()'>"

    """Delete book from the database"""
    if request.method == 'POST':
        session.delete(deletingBook)
        session.commit()
        return redirect(url_for('showGenreBooks', genre_name=genre.name))
    else:
        return render_template('deleteBook.html', book=deletingBook)

# Json End-Points
# API endpoints for all genres and books.


@app.route('/catalog.json')
def catalogJSON():
    genres = session.query(Genre).all()
    books = session.query(Book).all()
    return jsonify(Genres=[c.serialize for c in genres],
                   Books=[i.serialize for i in books])

# API endpoints for all genres.


@app.route('/genres.json')
def genresJSON():
    genres = session.query(Genre).all()
    return jsonify(Genres=[c.serialize for c in genres])

# API endpoints for all books of a specific genre.


@app.route('/<genre_name>/books.json')
def booksJSON(genre_name):
    genre = session.query(Genre).filter_by(name=genre_name).one()
    books = session.query(Book).filter_by(genre=genre).all()
    return jsonify(Books=[i.serialize for i in books])


if __name__ == '__main__':
    app.secret_key = 'APP_SECRET_KEY'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
