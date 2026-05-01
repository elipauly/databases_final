from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "User"

    userID = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))
    password = Column(String(100))
    ratings = relationship("Ratings", back_populates="user")

class Song(Base):
    __tablename__ = "Song"

    songID = Column(Integer, primary_key=True)
    songName = Column(String(100))
    albumID = Column(Integer, ForeignKey("Album.albumID"))
    album = relationship("Album")
    ratings = relationship("Ratings", back_populates="song")

class Ratings(Base):
    __tablename__ = "Ratings"

    userID = Column(Integer, ForeignKey("User.userID"), primary_key=True)
    songID = Column(Integer, ForeignKey("Song.songID"), primary_key=True)
    rating = Column(Integer)
    comments = Column(String(255))
    user = relationship("User", back_populates="ratings")
    song = relationship("Song", back_populates="ratings")

class Album(Base):
    __tablename__ = "Album"

    albumID = Column(Integer, primary_key=True)
    albumName = Column(String(100))

