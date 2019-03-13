from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from database_setup import *

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Delete Genres if exisitng.
session.query(Genre).delete()
# Delete Books if exisitng.
session.query(Book).delete()
# Delete Users if exisitng.
session.query(User).delete()

# Create sample users
User1 = User(name="Ambika",
             email="ambikapuvvula@gmail.com",
             picture='https://lh3.googleusercontent.com'
                     '/-yZwUmfIkJ1g/AAAAAAAAAAI/AAAAAAAAAAA'
                     '/qvFVyt25kJQ/W96-H96/photo.jpg')
session.add(User1)
session.commit()


# Create sample categories
Genre1 = Genre(name="Literature & Fiction",
               user_id=1)
session.add(Genre1)
session.commit()

Genre2 = Genre(name="Romance",
               user_id=1)
session.add(Genre2)
session.commit

Genre3 = Genre(name="Self Help Books",
               user_id=1)
session.add(Genre3)
session.commit()

Genre4 = Genre(name="Auto Biography",
               user_id=1)
session.add(Genre4)
session.commit()

Genre5 = Genre(name="Indian Writings",
               user_id=1)
session.add(Genre5)
session.commit()


# Populate a genre with books for testing
# Using different users for books also
Book1 = Book(name="Where the Forest meets the stars",
             date=datetime.datetime.now(),
             description="In this gorgeously stunning debut,"
             "a mysterious child teaches two strangers how to love"
             "and trust again.",
             image="https://images-na.ssl-images-amazon.com/images/I/"
             "918hXn4Uy1L.__BG0,0,0,0_FMpng_AC_UL200_SR200,200_.jpg",
             genre_id=1,
             user_id=1)
session.add(Book1)
session.commit()

Book2 = Book(name="Who Moved my cheese",
             date=datetime.datetime.now(),
             description="It is a parable that takes place in a maze."
             "Four beings live in that maze: Sniff and Scurry are"
             "mice--nonanalytical and nonjudgmental,"
             "they just want cheese and are willing to do whatever"
             "it takes to get it",
             image="https://images-na.ssl-images-amazon.com/images/"
             "I/51QGl7HfNyL._SX314_BO1,204,203,200_.jpg",
             genre_id=3,
             user_id=1)
session.add(Book2)
session.commit()

Book3 = Book(name="All Rights Reserved for you",
             date=datetime.datetime.now(),
             description="Every relationship requires effort but a"
             "long-distance relationship requires extra effort"
             "Aditya is a writer while the mere thought of reading repels"
             "Jasmine.They have absolutely nothing in common."
             "Not even the cities they live in.Yet nothing can stop them"
             "from falling head over heels for each other. ",
             image="https://images-na.ssl-images-amazon.com/images/"
             "I/51vY1PBcF1L._SX324_BO1,204,203,200_.jpg",
             genre_id=2,
             user_id=1)
session.add(Book3)
session.commit()

Book4 = Book(name="Charles chapliin my Autobiography",
             date=datetime.datetime.now(),
             description="Born into a theatrical family, Chaplin's father died"
             "of drink while his mother,"
             "unable to bear the poverty, suffered from bouts of insanity,"
             "Chaplin embarked on a film-making career which won him"
             "immeasurable success,as well as intense controversy."
             "His extraordinary autobiography"
             "was first published in 1964 and was written almost entirely"
             "without reference to documentation - simply as an astonishing"
             "feat of memory by a 75 year old man.",
             image="https://images-eu.ssl-images-amazon.com"
             "/images/I/41%2B2mHlfexL.jpg",
             genre_id=4,
             user_id=1)
session.add(Book4)
session.commit()

print("Your database has been populated with sample books!")
