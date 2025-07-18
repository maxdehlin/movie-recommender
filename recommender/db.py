import os
from dotenv import load_dotenv
import csv

from sqlalchemy import create_engine, String, text, and_
from sqlalchemy.orm import sessionmaker
from recommender.models import Base, MovieSimilarity, User, Rating
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# factory that gives a SessionLocal for any URL
def make_session_factory(db_url: str):
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


# DEPRECATED: switching from Movies in database
# def insert_movies(session, movies):
#     batch = [
#         Movie(id=row.movieId, title=row.title, genres=row.genres)
#         for row in movies.itertuples()
#     ]
#     session.bulk_save_objects(batch)
#     session.commit()
#     session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def insert_all_similarities(session, anchor_ids, neighbor_ids, weighted_sims):
    batch = []

    session.query(MovieSimilarity).delete()
    session.commit()
    # anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims
    for (a_id, n_id, w_sim) in zip(
        anchor_ids, neighbor_ids, weighted_sims
    ):
        batch.append(
            MovieSimilarity(
                movie_id=a_id,
                neighbor_id=n_id,
                weighted_sim=w_sim,
            )
        )

    # Bulk‐save
    session.bulk_save_objects(batch)
    session.commit()


def insert_user(session, google_id, email, name):
    try:
        user = session.query(User).filter_by(google_id=google_id).first()
    except OperationalError:
        session.rollback()
        raise print(status_code=500, detail="Database connection lost.")
    except Exception:
        session.rollback()
        raise

    if not user:
        user = User(google_id=google_id, email=email, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


# change this to not be a named relation. just an int and a movie_id int
def insert_rating_in_db(session, user_id, movie_id, value):
    try:
        rating = session.query(Rating).filter_by(user_id=user_id, movie_id=movie_id).first()
        if not rating:
            rating = Rating(user_id=user_id, movie_id=movie_id, value=value)
            session.add(rating)
            session.commit()
            session.refresh(rating)
            return True
        return False
    except Exception:
        session.rollback()
        raise

# DEPRECATED: switching from Movies in database
# def load_movies_from_csv(session, csv_path):
#     movies_data = []
#     movie_ids = set()
#     with open(csv_path, newline="") as f:
#         reader = csv.DictReader(f)
#         for i, row in enumerate(reader, 1):
#             movie_id = int(row["movieId"])
#             movie_ids.add(movie_id)
#             movies_data.append({
#                 "id": movie_id,
#                 "title": row["title"],
#                 "genres": row["genres"],
#             })
#             if i % 100_000 == 0:
#                 print(f"Read {i} movies...")

#     existing = {
#         mid for (mid,) in
#         session.query(Movie.id)
#                .filter(Movie.id.in_(movie_ids))
#                .all()
#     }

#     new_movies = [m for m in movies_data if m["id"] not in existing]
#     print(f"Inserting {len(new_movies)} new movies (skipped {len(movies_data) - len(new_movies)})")

#     session.bulk_insert_mappings(Movie, new_movies)
#     session.commit()


def reset_and_populate(session):
    # truncate child table first, then parent
    session.execute(text("TRUNCATE TABLE movies CASCADE;"))
    session.commit()


DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
