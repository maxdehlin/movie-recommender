import time
import os
import asyncio
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from jose import jwt
from recommender.db import get_db, insert_user
from recommender.models import User
from recommender.recommender import MovieRecommender
from schemas import Seeds
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

from jose import jwt, JWTError


# Load environment variables from a “.env” file 
config = Config(environ=os.environ)

client_id = os.getenv("DEV_GOOGLE_CLIENT_ID")
client_secret = os.getenv("DEV_GOOGLE_CLIENT_SECRET")
APP_ENV = os.getenv("APP_ENV")
FRONTEND_URL = os.getenv("FRONTEND_URL")



# load_dotenv()
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# JWT settings
JWT_SECRET = config("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 3600


# Define app with lifespan recommender
recommender = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global recommender
    loop = asyncio.get_event_loop()
    recommender = await loop.run_in_executor(None, MovieRecommender)
    print('Recommender is ready!')
    yield

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        FRONTEND_URL
        ], # add remote origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET") or "some‐random-string",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL environment variable not set")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)


def verify_jwt(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid JWT payload")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/auth/google/login")
async def google_login(request: Request):
    """
    Redirect single-page frontend (or any client) to Google's consent screen.
    """
    redirect_uri = str(request.url_for("google_callback"))
    if APP_ENV == 'prod':
        redirect_uri = redirect_uri.replace("http://", "https://")    
    return await oauth.google.authorize_redirect(request, redirect_uri)

from fastapi.responses import RedirectResponse


@app.get("/auth/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    session: Session = Depends(get_db)):
    """
    Google will redirect back here with a "code" query param.
    We exchange it for tokens, verify the ID token, upsert the User,
    and return a JWT for the frontend to store/use on subsequent requests.
    """
    # exchange "code" for tokens & get userinfo
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

    # extract Google's unique user ID and other profile fields
    google_id = user_info["sub"]
    email = user_info["email"]
    name = user_info.get("name", "")
    print('callback')
    
    user = insert_user(session, google_id, email, name)

    # generate a JWT so the frontend can call protected APIs
    expire = int(time.time() + JWT_EXPIRE_SECONDS)
    payload = {
        "sub": str(user.id),
        "exp": expire,
    }
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    redirect_url = f"{FRONTEND_URL}/?token={access_token}"
    print(FRONTEND_URL)
    return RedirectResponse(redirect_url)

@app.get("/verify_movie")
async def verify_movie(
    movie: str,
    user_id: str = Depends(verify_jwt)
):
    result = recommender.verify_movie_in_db(movie)
    if result:
        message = "Movie verified"
    else:
        message = "Invalid movie"
    return {"success": result, "detail": message}

@app.get("/user/ratings")
async def get_ratings(
    user_id: str = Depends(verify_jwt),
    session: Session = Depends(get_db)
):
    ratings = recommender.get_user_ratings(session, user_id)
    success = bool(ratings)
    return {"success": success, "detail": ratings}


from schemas import RatingRequest

@app.post("/user/ratings")
async def save_rating(
    rating: RatingRequest,

    user_id: str = Depends(verify_jwt),
    session: Session = Depends(get_db)

):
    success = recommender.insert_rating(session, user_id, rating.movie, rating.value)
    return {"success": success}



@app.post("/recommend")
async def get_recommendations(
    seeds: Seeds, user_id: str = Depends(verify_jwt),
    session: Session = Depends(get_db)
    ):
    print('seeds', seeds)
    # recommend movies based on seeds
    message = recommender.recommend_movies(session, seeds.seeds)

    # save seeds
    success = bool(message)
    return {"success": success, "detail": message}

# Backend API endpoints needed:
# GET /user/ratings - Get user's ratings
# POST /user/ratings - Save/update a rating
# DELETE /user/ratings/{movieId} - Delete a rating

@app.get("/dev/movies")
async def get_dev_movies():
    """
    Development-only endpoint that returns mock movie data for frontend development.
    This endpoint should never be used in production.
    """
    print('API CALLED')
    if APP_ENV == "prod":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is not available in production"
        )
    
    import json
    try:
        with open("mock_data.json", "r") as f:
            mock_data = json.load(f)
        print(mock_data)
        return mock_data
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Mock data file not found"
        )

@app.get("/dev/random-movies")
async def get_random_dev_movies(count: int = 5):
    """
    Development-only endpoint that returns a random selection of movies for rating.
    This endpoint should never be used in production.
    """
    if APP_ENV == "prod":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is not available in production"
        )
    
    import json
    import random
    try:
        with open("mock_data.json", "r") as f:
            mock_data = json.load(f)
        
        # Return random selection of movies
        random_movies = random.sample(mock_data["movies"], min(count, len(mock_data["movies"])))
        return {"movies": random_movies}
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Mock data file not found"
        )

@app.post("/dev/mock-recommend")
async def mock_recommend(user_id: str = Depends(verify_jwt)):
    """
    Development-only endpoint that returns mock recommendations.
    This endpoint should never be used in production.
    """
    if APP_ENV == "prod":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is not available in production"
        )
    
    import json
    try:
        with open("mock_data.json", "r") as f:
            mock_data = json.load(f)
        
        return {
            "success": True,
            "detail": mock_data["recommendations"]
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Mock data file not found"
        )

@app.post("/auth/dev-login")
async def dev_login(session: Session = Depends(get_db)):
    """
    Development-only endpoint that returns a JWT token without Google OAuth.
    This endpoint should never be used in production.
    """
    if APP_ENV == "prod":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is not available in production"
        )
    
    # Create or get test user
    test_user = insert_user(
        session,
        google_id=None,  # No Google ID for dev login
        email="dev@example.com",
        name="Development User"
    )
    
    # Generate JWT token
    expire = int(time.time() + JWT_EXPIRE_SECONDS)
    payload = {
        "sub": str(test_user.id),
        "exp": expire,
    }
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": test_user.id,
            "email": test_user.email,
            "name": test_user.name
        }
    }
