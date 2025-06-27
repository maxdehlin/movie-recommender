import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from dotenv import load_dotenv
from sklearn.neighbors import NearestNeighbors
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
import heapq
import os
from recommender.models import MovieSimilarity, Movie, Rating
from recommender.db import get_db, insert_rating_in_db


url = os.getenv("DATABASE_URL")

# load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

small = 'data/ml-latest-small'
big = 'data/ml-32m'


class MovieRecommender:
    def __init__(self, folder='data/ml-32m'):
        # self.db_url = db_url or os.getenv('DATABASE_URL')
        # if not self.db_url:
        #     raise RuntimeError("DATABASE_URL not set")
        # if self.db_url.startswith("postgres://"):
        #     self.db_url = self.db_url.replace("postgres://", "postgresql+psycopg2://", 1)

        self.folder = folder
        self.ratings = None
        self.movies = None

        self.movie_titles = {}
        self.movie_inv_titles = {}
        self.create_mappings(next(get_db()))


    def tester(self):
        print(self.movie_inv_titles)

    
    def import_data(self, folder):
        # get the directory where this .py file lives
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(BASE_DIR, folder)
        self.ratings = pd.read_csv(os.path.join(data_folder, "ratings.csv"))
        self.movies  = pd.read_csv(os.path.join(data_folder, "movies.csv"))

    def create_mappings(self, session):
        movies = session.query(Movie).all()
        self.movie_titles = {movie.id: movie.title for movie in movies}
        self.movie_inv_titles = {movie.title: movie.id for movie in movies}


    # Generates a sparse utility matrix
    def create_X(self, df):
        M = df['userId'].nunique()
        N = df['movieId'].nunique()

        user_mapper = dict(zip(np.unique(df["userId"]), list(range(M))))
        movie_mapper = dict(zip(np.unique(df["movieId"]), list(range(N))))
        
        user_inv_mapper = dict(zip(list(range(M)), np.unique(df["userId"])))
        movie_inv_mapper = dict(zip(list(range(N)), np.unique(df["movieId"])))
        
        user_index = [user_mapper[i] for i in df['userId']]
        item_index = [movie_mapper[i] for i in df['movieId']]

        X = csr_matrix((df["rating"], (user_index,item_index)), shape=(M,N))
        
        return X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper

    # calculate similarities for all pairs of movies
    def calculate_similarities(self):
        X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper = self.create_X(ratings)
        movie_titles = dict(zip(self.movies['movieId'], self.movies['title']))

        X_csc = X.tocsc()  # shape = (n_users, n_items)

        n_items = X_csc.shape[1]
        # supports[i] = set of user‐indices who rated item i
        supports = []
        for i in range(n_items):
            # nonzero()[0] gives the row‐indices of nonzero entries in column i
            users_who_rated_i = set(X_csc[:, i].nonzero()[0])
            supports.append(users_who_rated_i)

        # fit NearestNeighbors on the (n_items × n_users) transpose:
        item_features = X_csc.T  # now shape = (n_items, n_users), still sparse

        K = 15
        nn = NearestNeighbors(
            n_neighbors=K + 1,
            metric="cosine",
            algorithm="brute",
            n_jobs=-1,
        )
        nn.fit(item_features)

        distances, indices = nn.kneighbors(item_features, return_distance=True)

        alpha = 10  # shrinkage parameter
        anchor_ids = []
        neighbor_ids = []
        raw_sims   = []
        co_counts  = []
        weighted_sims = []

        for i in range(n_items):
            anchor_id = movie_inv_mapper[i]
            for rank in range(1, K+1):
                j = indices[i][rank]
                neighbor_id = movie_inv_mapper[j]

                if anchor_id < neighbor_id:
                    raw_sim = 1.0 - distances[i][rank]
                    co_cnt  = len(supports[i] & supports[j])
                    shrink  = co_cnt / (co_cnt + alpha)
                    w_sim   = raw_sim * shrink

                    anchor_ids.append(int(anchor_id))
                    neighbor_ids.append(int(neighbor_id))
                    raw_sims.append(float(raw_sim))
                    co_counts.append(co_cnt)
                    weighted_sims.append(float(w_sim))
        return anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims

    # query database to find movies with highest similarity movies for a given movie id
    def topk_movies(self, session, movie_id, k):
        rows = (
            session.query(MovieSimilarity)
                .filter(
                    or_(
                        MovieSimilarity.movie_id   == movie_id,
                        MovieSimilarity.neighbor_id == movie_id
                    )
                    
                )
                .order_by(MovieSimilarity.weighted_sim.desc())
                .all()
        )
        session.close()
        return rows[:k]

    # find highest rated movies from a set of rated seed movies
    def find_highly_rated_movies(self, seed_movies):
        minimum_seed_count = 3
        high_rating_threshold = 4.0
        sorted_movies = sorted(seed_movies, key=lambda x: x[1], reverse=True)
        output = []
        for i in range(len(sorted_movies)):
            movie = sorted_movies[i]
            if movie[1] < high_rating_threshold and len(output) > minimum_seed_count:
                break
            output.append(movie[0])
        return output



    # find recommended movies from a set of seed movies
    def find_recommended_movies(self, session, seed_ratings):
        seed_movies = set([x[0] for x in seed_ratings])
        
        rated_movies = self.find_highly_rated_movies(seed_ratings)
        heap = []
        lists = []
        k_recommended = 10

        for i in range(len(rated_movies)):
            list = self.topk_movies(session, rated_movies[i], k_recommended)
            lists.append(list)
            elem = list[0]
            score = -elem.weighted_sim # negative score so its descending order
            heap.append((score, i, 0, elem))
        heapq.heapify(heap)


        result = []
        while heap:
            score, i, j, elem = heapq.heappop(heap)
            movie_id = elem.movie_id
            neighbor_id = elem.neighbor_id

            if movie_id not in seed_movies:
                result.append(movie_id)
            if neighbor_id not in seed_movies:
                result.append(neighbor_id)

            # advance in list i
            if j + 1 < len(lists[i]):
                nxt = lists[i][j + 1]
                nxt_score = -nxt.weighted_sim
                heapq.heappush(heap, (nxt_score, i, j + 1, nxt))
        return result

    # recommends k movies based on given titles
    # expect movie_ratings = [(movie_title, rating), ...]
    def recommend_movies(self, session,  movie_ratings, k=5):
        print([x.title for x in movie_ratings])
        seed_movies = [(self.movie_inv_titles[x.title], x.rating) for x in movie_ratings]
        rec_movie_ids = self.find_recommended_movies(session, seed_movies)[:k]
        rec_movie_titles = [self.movie_titles[x] for x in rec_movie_ids]
        return rec_movie_titles

    def verify_movie_in_db(self, title):
        exists = title in self.movie_inv_titles
        if exists:
            print("Movie exists")
        else:
            print("Movie does not exist")
        return exists

    def get_user_ratings(self, session, user_id):
        try:
            ratings = session.query(Rating).filter(Rating.user_id == user_id).all()
            return ratings
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Failed to fetch ratings for user {user_id}: {e}")
            return []

    def insert_rating(self, session, user_id, movie, value):
        try:
            movie_id = self.movie_inv_titles[movie]
            if not movie_id:
                return False
            print('Balls3')
            print(movie)
            print(value)
            print(user_id)
            print('Balls4')
            success = insert_rating_in_db(session, user_id, movie_id, value)
            return success
        except Exception:
            raise



            
