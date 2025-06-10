from db import load_movies_from_csv, load_users_and_ratings, make_session_factory
import os
from dotenv import load_dotenv
load_dotenv()

def main():
    movies_path = "recommender/data/ml-32m/movies.csv"
    ratings_path = "recommender/data/ml-32m/ratings.csv"
    url = os.getenv("REMOTE_DATABASE_URL")  # e.g. "postgres://user:pass@host/db"
    # SQLAlchemy wants "postgresql+psycopg2://…"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    SessionLocal = make_session_factory(url)





    session = SessionLocal()
    try:
        load_movies_from_csv(session, movies_path)
        load_users_and_ratings(session, ratings_path)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
