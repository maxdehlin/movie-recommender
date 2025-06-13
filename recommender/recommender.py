import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from dotenv import load_dotenv
from sklearn.neighbors import NearestNeighbors
import os
from .models import MovieSimilarity, Movie
from sqlalchemy import or_
import heapq
from .db import make_session_factory

url = os.getenv("LOCAL_DATABASE_URL")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)

SessionLocal = make_session_factory(url)





session = SessionLocal()

load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

small = 'data/ml-latest-small'
big = 'data/ml-32m'

folder = big


# get the directory where this .py file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# point to the “data” folder inside it
data_folder = os.path.join(BASE_DIR, folder)
# print(data_folder)

# now these will work no matter where you run the script from
# ratings = pd.read_csv(os.path.join(data_folder, "ratings.csv"))
movies  = pd.read_csv(os.path.join(data_folder, "movies.csv"))

ratings = pd.DataFrame()
# ratings = pd.read_csv(f'{folder}/ratings.csv')

# movies = pd.read_csv(f'{folder}/movies.csv')
user_mapper = {}
movie_mapper = {}
user_inv_mapper = {}
movie_inv_mapper = {}
movie_titles = dict(zip(movies['movieId'], movies['title']))
movie_inv_titles = dict(zip(movies['title'], movies['movieId']))


# Generates a sparse utility matrix
def create_X(df):
    """
    Args:
        df: pandas dataframe containing 3 columns (userId, movieId, rating)
    
    Returns:
        X: sparse matrix
        user_mapper: dict that maps user id's to user indices
        user_inv_mapper: dict that maps user indices to user id's
        movie_mapper: dict that maps movie id's to movie indices
        movie_inv_mapper: dict that maps movie indices to movie id's
    """
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
def calculate_similarities():
    X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper = create_X(ratings)
    movie_titles = dict(zip(movies['movieId'], movies['title']))

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
def topk_movies(session, movie_id, k):
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
def find_highly_rated_movies(seed_movies):
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
def find_recommended_movies(session, seed_ratings):
    seed_movies = set([x[0] for x in seed_ratings])
    
    rated_movies = find_highly_rated_movies(seed_ratings)
    heap = []
    lists = []
    k_recommended = 10

    for i in range(len(rated_movies)):
        list = topk_movies(session, rated_movies[i], k_recommended)
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
def recommend_movies(session, movie_ratings, k):
    seed_movies = [(movie_inv_titles[x[0]], x[1]) for x in movie_ratings]
    rec_movie_ids = find_recommended_movies(session, seed_movies)[:k]
    rec_movie_titles = [movie_titles[x] for x in rec_movie_ids]
    return rec_movie_titles

from sqlalchemy import select, exists




def verify_movie_in_db(title):
    exists = title in movie_inv_titles
    if exists:
        print("Movie exists")
    else:
        print("Movie does not exist")
    return exists





seed_movies = [(1, 5.0), (2, 3.5), (3, 5.0),(4, 2.5), (5, 4.0),
               (6, 1.5),  (7, 1.0),  (8, 3.0),  (9, 2.5),  (10, 2.5),
    (11, 2.0), (12, 1.5), (13, 5.0), (14, 1.5), (15, 4.0),
    (16, 1.0), (17, 1.0), (18, 1.5), (19, 2.5), (20, 2.5),
    (21, 5.0), (22, 2.5), (23, 2.5), (24, 3.0), (25, 3.0),
    (26, 4.0), (27, 2.0), (28, 4.5), (29, 1.5), (30, 2.5),
    (31, 4.5), (32, 3.5), (33, 2.0), (34, 1.5), (35, 1.0),
    (36, 2.0), (37, 3.0), (38, 1.0), (39, 4.5), (40, 2.0),
    (41, 3.0), (42, 3.5), (43, 3.0), (44, 1.5), (45, 1.5),
    (46, 3.0), (47, 1.5), (48, 3.5), (49, 2.0), (50, 1.0),
    (51, 2.5), (52, 1.5), (53, 3.5), (54, 1.5), (55, 3.0),
    (57, 3.5), (58, 4.5), (59, 2.5), (60, 3.5),
    (61, 1.5), (62, 3.0), (63, 3.5), (64, 1.0), (65, 3.0),
    (66, 4.5), (67, 2.5), (68, 2.0), (69, 5.0), (70, 4.0),
    (71, 2.5), (72, 1.0), (73, 1.0), (74, 4.0), (75, 3.5),
    (76, 3.0), (77, 3.5), (78, 2.0), (79, 4.0), (80, 3.0),
    (81, 2.0), (82, 4.5), (83, 5.0), (85, 2.0),
    (86, 3.5), (87, 1.5), (88, 2.0), (89, 1.0), (90, 3.5),
    (91, 2.5), (92, 4.5), (93, 4.0), (94, 4.5), (95, 2.0),
    (96, 3.0), (97, 2.0), (98, 2.5), (99, 5.0), (100, 5.0),
    (101, 3.0), (102, 4.0), (103, 4.0), (104, 3.5), (105, 2.5),]

rated_movies = [('Toy Story (1995)', 5.0), ('Jumanji (1995)', 3.5), ('Grumpier Old Men (1995)', 5.0)]
# print(recommend_movies(session, rated_movies, 10))
