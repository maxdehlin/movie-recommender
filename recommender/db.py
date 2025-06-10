import os
from dotenv import load_dotenv
import csv

from sqlalchemy import create_engine, String, text
from sqlalchemy.orm import sessionmaker
from models import Base
from sqlalchemy.ext.declarative import declarative_base


from models import MovieSimilarity, Movie, User, Rating
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# factory that gives a SessionLocal for any URL
def make_session_factory(db_url: str):
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)

# retrieves data
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def insert_movies(session, movies):
    batch = [
        Movie(id=row.movieId, title=row.title, genres=row.genres)
        for row in movies.itertuples()
    ]
    session.bulk_save_objects(batch)
    session.commit()
    session.close()


def insert_all_similarities(session, anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims):
    batch = []
    # anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims
    for (a_id, n_id, r_sim, c_cnt, w_sim) in zip(
        anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims
    ):
        batch.append(
            MovieSimilarity(
                movie_id=a_id,
                neighbor_id=n_id,
                raw_sim=r_sim,
                co_count=c_cnt,
                weighted_sim=w_sim,
            )
        )

    # Bulk‐save
    session.bulk_save_objects(batch)
    session.commit()


def insert_user(session, google_id, email, name):
    user = session.query(User).filter_by(google_id=google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def insert_rating(session, user_id, movie_id, value):
    rating = session.query(Rating).filter_by(user_id=user_id, movie_id=movie_id).first()
    if not rating:
        rating = Rating(user_id=user_id, movie_id=movie_id, value=value)
        session.add(rating)
        session.commit()
        session.refresh(rating)
    return rating

# db.py
def load_movies_from_csv(session, csv_path: str):
    print("Loading movies")
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        batch = []
        for i, row in enumerate(reader, 1):
            if i % 100_000 == 0:
                print(f"  {i} movies…")
            batch.append(
                Movie(
                    id=int(row["movieId"]),
                    title=row["title"],
                    genres=row["genres"],
                )
            )
        session.bulk_save_objects(batch)
        session.commit()
    print(f"Inserted {len(batch)} movies")


def load_users_and_ratings(session, csv_path: str):
    print("Loading users & ratings")
    user_ids = set()
    ratings_data = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            if i % 10_000 == 0:
                print(f"  {i} ratings…")
            uid = int(row["userId"])
            user_ids.add(uid)
            ratings_data.append({
                "user_id":  uid,
                "movie_id": int(row["movieId"]),
                "value":    float(row["rating"]),
                "timestamp": int(row["timestamp"]),
            })

    # only insert new users
    existing = {
        uid for (uid,) in session.query(User.id)
                                 .filter(User.id.in_(user_ids))
                                 .all()
    }
    new_ids = user_ids - existing
    session.bulk_save_objects([
        User(id=uid, is_import=True)
        for uid in new_ids
    ])
    session.flush()

    # insert all ratings
    session.bulk_insert_mappings(Rating, ratings_data)
    session.commit()

    # fix the users sequence
    session.execute(text(
        "SELECT setval(pg_get_serial_sequence('users','id'), (SELECT MAX(id) FROM users));"
    ))
    session.commit()

    print(f"Inserted {len(new_ids)} users and {len(ratings_data)} ratings")

def reset_and_populate(session):
    # truncate child table first, then parent
    session.execute(text("TRUNCATE TABLE movies CASCADE;"))
    session.commit()
