from db import load_movies_from_csv, load_users, make_session_factory, text
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
    SessionLocal = make_session_factory(url)





    session = SessionLocal()
    try:
        load_movies_from_csv(session, movies_path)
        load_users(session, ratings_path)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
