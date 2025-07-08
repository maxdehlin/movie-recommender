from recommender.db import get_db, insert_all_similarities
from recommender.recommender import MovieRecommender
import os
from dotenv import load_dotenv
load_dotenv()



def main():
    folder = "ml-32"
    movies_path = f"recommender/data/{folder}/movies.csv"
    # ratings_path = f"recommender/data/{folder}/ratings.csv"
    # url = os.getenv("DATABASE_URL")
    # if url.startswith("postgres://"):
    #     url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    # SessionLocal = make_session_factory(url)
    # session = SessionLocal()
    session = next(get_db())

    recommender = MovieRecommender()

    try:
        print('Importing ratings')
        recommender.import_ratings()
        print('Calculating similarities')
        anchor_ids, neighbor_ids, weighted_sims = recommender.calculate_similarities()
        print('Saving Similarities')
        insert_all_similarities(session, anchor_ids, neighbor_ids, weighted_sims)
        session.commit()
    except:
        print('Exception')
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()