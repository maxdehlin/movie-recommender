from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Index,
    String,
    PrimaryKeyConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Movie(Base):
    __tablename__ = "movies"
    id    = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genres = Column(String, nullable=False)

    neighbors = relationship(
        "MovieSimilarity",
        back_populates="movie",
        foreign_keys="[MovieSimilarity.movie_id]"
    )

    ratings = relationship("Rating", back_populates="movie")


class MovieSimilarity(Base):
    __tablename__ = "movie_similarities"
    movie_id     = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    neighbor_id  = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    raw_sim      = Column(Float,  nullable=False)
    co_count     = Column(Integer, nullable=False)
    weighted_sim = Column(Float,  nullable=False)

    movie = relationship(
        "Movie",
        foreign_keys=[movie_id],
        back_populates="neighbors"
    )
    neighbor = relationship(
        "Movie",
        foreign_keys=[neighbor_id]
    )

    __table_args__ = (
        Index("ix_movie_similarities_movie_id_weighted_sim", "movie_id", "weighted_sim"),
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)

    ratings = relationship("Rating", back_populates="user")

class Rating(Base):
    __tablename__ = 'ratings'

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    value = Column(Float, nullable=False)


    user = relationship("User", back_populates="rating")
    movie = relationship("Movie", back_populates="rating")

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "movie_id", name="pk_user_movie"),
    )

 