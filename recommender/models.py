from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Index,
    String,
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


class MovieSimilarity(Base):
    __tablename__ = "movie_similarities"
    movie_id     = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    neighbor_id  = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    raw_sim      = Column(Float,  nullable=False)
    co_count     = Column(Integer, nullable=False)
    weighted_sim = Column(Float,  nullable=False)

    movie    = relationship(
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