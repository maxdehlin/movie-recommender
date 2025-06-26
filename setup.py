from recommender.db import load_movies_from_csv, get_db, text
from recommender.recommender import MovieRecommender
import os
from dotenv import load_dotenv
load_dotenv()



def main():
    folder = "ml-latest-small"
    movies_path = f"recommender/data/{folder}/movies.csv"
    ratings_path = f"recommender/data/{folder}/ratings.csv"
    url = os.getenv("TEST_DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    # SessionLocal = make_session_factory(url)
    # session = SessionLocal()
    session = next(get_db())

    # recommender = MovieRecommender()

    try:
        load_movies_from_csv(session, movies_path)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()