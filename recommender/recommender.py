import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.spatial.distance import cosine
from dotenv import load_dotenv
from sklearn.neighbors import NearestNeighbors
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
import heapq
import os
from recommender.models import MovieSimilarity, Rating
from recommender.db import get_db, insert_rating_in_db
from recommender.helpers import normalize
from collections import namedtuple



url = os.getenv("DATABASE_URL")

# load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

small = 'data/ml-latest-small'
big = 'data/ml-32m'


Movie = namedtuple("Movie", ["id", "title", "genres"])


class MovieRecommender:
    def __init__(self, folder=small):
        # self.db_url = db_url or os.getenv('DATABASE_URL')
        # if not self.db_url:
        #     raise RuntimeError("DATABASE_URL not set")
        # if self.db_url.startswith("postgres://"):
        #     self.db_url = self.db_url.replace("postgres://", "postgresql+psycopg2://", 1)

        self.folder = folder
        self.ratings = None
        self.movies = None
        self.movies_df = None
        self.high_support_movies = None

        self.movie_titles = {}
        self.movie_inv_titles = {}
        print("Initializing recommender...")
        self.import_ratings()
        self.import_movies()
        self.calculate_similarities()
        self.create_mappings()


    def tester(self):
        print(self.high_support_movies)

    
    def import_movies(self):
        # get the directory where this .py file lives
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(BASE_DIR, self.folder)
        print(f'Reading movies from {data_folder}/movies.csv')
        self.movies_df = pd.read_csv(os.path.join(data_folder, "movies.csv"))

    
    def import_ratings(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(BASE_DIR, self.folder)
        print(f'Reading ratings from {data_folder}/ratings.csv')
        self.ratings = pd.read_csv(os.path.join(data_folder, "ratings.csv"))


    def create_mappings(self):
        movie_list = [
            Movie(id=row["movieId"], title=row["title"], genres=row["genres"])
            for _, row in self.movies_df.iterrows()
        ]
        self.movies = movie_list
        self.movie_titles = {movie.id: movie.title for movie in self.movies}
        # normalize title for easy of search later on
        self.movie_inv_titles = {normalize(movie.title): movie.id for movie in self.movies}


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
        X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper = self.create_X(self.ratings)
        # movie_titles = dict(zip(self.movies['movieId'], self.movies['title']))

        X_csc = X.tocsc()  # shape = (n_users, n_items)

        self.X_csc = X_csc
        self.movie_mapper = movie_mapper
        self.movie_inv_mapper = movie_inv_mapper

        n_items = X_csc.shape[1]
        # supports[i] = set of user‐indices who rated item i
        supports = []
        for i in range(n_items):
            movie_id = movie_inv_mapper[i]
            # nonzero()[0] gives the row‐indices of nonzero entries in column i
            users_who_rated_i = set(X_csc[:, i].nonzero()[0])
            supports.append((movie_id, users_who_rated_i))

        top_n = 10000
        top_items = sorted(supports, key=lambda x: len(x[1]), reverse=True)[:top_n]


        top_movie_ids = set(int(movie_id) for movie_id, _ in top_items)
        supports_dict = {movie_id: users for movie_id, users in top_items}

        self.high_support_movies = top_movie_ids

        

        item_features = X_csc.T  # now shape = (n_items, n_users), still sparse
 
        K = 10
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
        # raw_sims   = []
        # co_counts  = []
        weighted_sims = []

        for i in range(n_items):
            movie_id_i = movie_inv_mapper[i]
            if movie_id_i not in top_movie_ids:
                continue

            for rank in range(1, K + 1):
                j = indices[i][rank]
                movie_id_j = movie_inv_mapper[j]
                if movie_id_j not in top_movie_ids:
                    continue

                if movie_id_i < movie_id_j:
                    raw_sim = 1.0 - distances[i][rank]
                    co_cnt = len(supports_dict[movie_id_i] & supports_dict[movie_id_j])
                    shrink = co_cnt / (co_cnt + alpha)
                    w_sim = raw_sim * shrink

                    anchor_ids.append(int(movie_id_i))
                    neighbor_ids.append(int(movie_id_j))
                    weighted_sims.append(float(w_sim))
        # return anchor_ids, neighbor_ids, raw_sims, co_counts, weighted_sims
        return anchor_ids, neighbor_ids, weighted_sims
    

    def high_support_similarities(self, movie_id):
        print('running high support similarities')
        # sparse user vector for the rare movie
        movie_col = self.movie_mapper[movie_id]
        v = self.X_csc[:, movie_col]  # shape = (n_users, 1)

        alpha = 10 # shrinkage factor
        sims = []
        for common_id in self.high_support_movies:
            j = self.movie_mapper[common_id]
            vj = self.X_csc[:, j]
            co_cnt = len(set(v.nonzero()[0]) & set(vj.nonzero()[0]))
            if co_cnt == 0:
                continue
            raw_sim = 1.0 - cosine(v.toarray().ravel(), vj.toarray().ravel())
            shrink = co_cnt / (co_cnt + alpha)

            sims.append(MovieSimilarity(
                movie_id=int(movie_id),
                neighbor_id=int(common_id),
                weighted_sim=float(raw_sim * shrink)
            ))

        # take top-K
        print('returning:', sims[0])
        return sorted(sims, key=lambda x: x.weighted_sim, reverse=True)


    # query database to find movies with highest similarity movies for a given movie id
    def topk_movies(self, session, movie_id, k):
        rows = None
        # try:
        # if movie is obscure, compute similarity with common movies only.
        if movie_id not in self.movies:
            print('Movie not found in self.movies:', movie_id)

        if movie_id not in self.high_support_movies:
            print('High support movies:', self.high_support_movies)
            print('Obscure movie found. Finding similar common movies...')
            print('Movie ID:', movie_id)
            rows = self.high_support_similarities(movie_id)[:k]
        else:
            print('Common movie found...')
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
        # except Exception as e:
        #     print('Error:', e)
        #     session.rollback()
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


    def find_recommended_movies(self, session, seed_ratings, max_results=50, k_per_seed=10):
        # movies the user already supplied/rated
        seed_movies = set([x[0] for x in seed_ratings])

        rated_movies = self.find_highly_rated_movies(seed_ratings)  # list of movie_ids

        heap = []
        lists = []

        # build top-k lists per anchor and prime  heap
        for i, anchor_id in enumerate(rated_movies):
            lst = self.topk_movies(session, anchor_id, k_per_seed)  # elements have .movie_id, .neighbor_id, .weighted_sim
            if not lst:
                continue
            lists.append(lst)
            elem = lst[0]
            score = -elem.weighted_sim  # min-heap => negative for descending
            heap.append((score, len(lists) - 1, 0, elem))

        if not heap:
            return []

        heapq.heapify(heap)

        result = []
        seen = set(seed_movies)  # start by excluding seeds

        while heap and len(result) < max_results:
            score, i, j, elem = heapq.heappop(heap)

            # treat the neighbor as the candidate recommendation
            candidate = elem.neighbor_id

            # exclude seeds and previously yielded items
            if candidate not in seen:
                result.append(candidate)
                seen.add(candidate)

            # advance within list i
            nxt_index = j + 1
            if nxt_index < len(lists[i]):
                nxt = lists[i][nxt_index]
                nxt_score = -nxt.weighted_sim
                heapq.heappush(heap, (nxt_score, i, nxt_index, nxt))

        return result


    # recommends k movies based on given titles
    # expect movie_ratings = [(movie_title, rating), ...]
    def recommend_movies(self, session,  movie_ratings, k=5):
        seed_movies = [(x.id, x.rating) for x in movie_ratings]
        rec_movie_ids = self.find_recommended_movies(session, seed_movies)[:k]
        rec_movie_titles = [self.movie_titles[x] for x in rec_movie_ids]
        return rec_movie_titles # change this to return movie_id and title


    # verifies that the movie exists
    # returns the official title of the movie if exists
    # returns empty string if the movie does not exist 
    def verify_movie_in_db(self, title):
        # fetch official title from movie_titles
        # the title parameter could be an unofficial variation
        normalized_title = normalize(title)
        if normalized_title in self.movie_inv_titles:

            movie_id = self.movie_inv_titles[normalized_title]
            official_title = self.movie_titles[movie_id]
            return official_title


        print("Movie does not exist")
        return ''


    # def get_user_ratings(self, session, user_id):
    #     try:
    #         ratings = session.query(Rating).filter(Rating.user_id == user_id).all()
    #         return ratings
    #     except SQLAlchemyError as e:
    #         session.rollback()
    #         print(f"Failed to fetch ratings for user {user_id}: {e}")
    #         return []
        
    def get_user_ratings(self, session, user_id):
        ratings = session.query(Rating).filter(Rating.user_id == user_id).all()
        result = []
        for r in ratings:
            title = self.movie_titles.get(r.movie_id)
            if title:
                result.append({
                    "title": title,
                    "rating": r.value,
                    "movie_id": r.movie_id,
                })
        return result


    def insert_rating(self, session, user_id, movie, value):
        print('huh')
        try:
            movie_id = self.movie_inv_titles[normalize(movie)] or False
            if not movie_id:
                print('no movie_id of this')
                return False
            success = insert_rating_in_db(session, user_id, movie_id, value)

            return success
        except Exception:
            raise
