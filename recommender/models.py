from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Index,
    String,
    Boolean,
    desc
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# class Movie(Base):
#     __tablename__ = "movies"
#     id    = Column(Integer, primary_key=True)
#     title = Column(String, nullable=False)
#     genres = Column(String, nullable=False)

#     neighbors = relationship(
#         "MovieSimilarity",
#         back_populates="movie",
#         foreign_keys="[MovieSimilarity.movie_id]"
#     )

#     ratings = relationship("Rating", back_populates="movie")




class MovieSimilarity(Base):
    __tablename__ = "movie_similarities"
    movie_id     = Column(Integer, primary_key=True)
    neighbor_id  = Column(Integer, primary_key=True)
    weighted_sim = Column(Float,  nullable=False)

    def __repr__(self):
        return f"<MovieSimilarity({self.movie_id} → {self.neighbor_id}, sim={self.weighted_sim:.4f})>"

    __table_args__ = (
        Index("ix_movie_similarities_movie_id_weighted_sim", "movie_id", desc("weighted_sim")),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)

    is_import = Column(Boolean, default=False, nullable=False)

    ratings = relationship("Rating", back_populates="user")


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(Integer)

    user = relationship("User", back_populates="ratings")
