
class Rating:
    def __init__(self, userId, movieId, rating, timestamp):
        self.userId = userId
        self.movieId = movieId
        self.rating = rating
        self.timestamp = timestamp

    def __repr__(self):
        return f"Rating(userId={self.userId}, movieId={self.movieId}, rating={self.rating},  rating={self.rating})"
    


    
class Profile:
    def __init__(self, userId, name):
        self.userId = userId
        self.name = name

    def __repr__(self):
        return f"Profile(userId={self.userId}, name={self.name})"
    
    def create_profile(user_id, profile_data):
        """
        Create a user profile in the database.
        """
        print(f"Profile created for user {user_id}: {profile_data}")
        return Profile(user_id, profile_data.get("name", "Unknown"))
    
    def add_rating(rating):
        """
        Add a rating to the database.
        """
        
        print(f"Rating added: {rating}")
    

class Movie:
    def __init__(self, movieId, title, genre):
        self.movieId = movieId
        self.title = title
        self.genre = genre

    def __repr__(self):
        return f"Movie(movieId={self.movieId}, title={self.title}, genre={self.genre})"
    

class MovieDatabase:
    def __init__(self):
        self.movies = {}
        self.profiles = {}
        self.ratings = []
    

                 

