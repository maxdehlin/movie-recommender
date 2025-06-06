import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from sqlalchemy.ext.declarative import declarative_base

from models import MovieSimilarity, Movie
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/movie_db"
engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def insert_movies(movies):
    session = SessionLocal()
    batch = [
        Movie(id=row.movieId, title=row.title, genres=row.genres)
        for row in movies.itertuples()
    ]
    session.bulk_save_objects(batch)
    session.commit()
    session.close()



def insert_all_similarities(anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims):
    session = SessionLocal()
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
    session.close()
# insert_movies()
# insert_all_similarities()

# def reset_and_populate():
#     session = SessionLocal()
#     # truncate child table first, then parent
#     session.execute(text("TRUNCATE TABLE movies CASCADE;"))
#     session.commit()
#     session.close()

#     # repopulate both tables
#     insert_movies()
#     insert_all_similarities()