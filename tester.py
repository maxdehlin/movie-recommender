from schemas import Seed
from recommender.recommender import MovieRecommender

seeds = [
    Seed(title='Toy Story (1995)', rating=5.0),
    Seed(title='Inception (2010)', rating=5.0),
    Seed(title='Jumanji (1995)', rating=5.0),
    Seed(title='Star Wars: Episode IV - A New Hope (1977)', rating=1.0),
    Seed(title='Black Beauty (1994)', rating=1.0),
    Seed(title='Die Hard (1988)', rating=1.0),
    Seed(title='Ring, The (2002)', rating=1.0),
    Seed(title='Antz (1998)', rating=5.0),
    Seed(title='Star Wars: Episode I - The Phantom Menace (1999)', rating=5.0),
    Seed(title="Ferris Bueller's Day Off (1986)", rating=5.0),
    Seed(title='Star Wars: Episode II - Attack of the Clones (2002)', rating = 1.0)
]


# movies = recommend_movies(seeds, 100)
recommender = MovieRecommender()
recommender.create_mappings()