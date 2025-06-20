import time
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from jose import jwt
from recommender.db import insert_user, make_session_factory
from recommender.models import User
from recommender.recommender import MovieRecommender
from schemas import Seeds
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
# Load environment variables from a “.env” file 
config = Config(environ=os.environ)

client_id = os.getenv("DEV_GOOGLE_CLIENT_ID")
client_secret = os.getenv("DEV_GOOGLE_CLIENT_SECRET")

recommender = MovieRecommender()

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
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # add remote origin
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


SessionLocal = make_session_factory(url)
session = SessionLocal()

def verify_jwt(token: str = Depends(oauth2_scheme)):
    print('token', token)
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
    Redirect single-page frontend (or any client) to Google’s consent screen.
    """
    redirect_uri = str(request.url_for("google_callback")).replace("http://", "https://")    
    return await oauth.google.authorize_redirect(request, redirect_uri)

from fastapi.responses import RedirectResponse

FRONTEND_URL = "http://localhost:5173"

@app.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    """
    Google will redirect back here with a “code” query param.
    We exchange it for tokens, verify the ID token, upsert the User,
    and return a JWT for the frontend to store/use on subsequent requests.
    """
    # exchange “code” for tokens & get userinfo
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

    # extract Google’s unique user ID and other profile fields
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
    return RedirectResponse(redirect_url)

@app.get("/verify_movie")
async def verify_movie(
    movie: str,
    user_id: str = Depends(verify_jwt)
):
    # print(movie)
    result = recommender.verify_movie_in_db(movie)
    if result:
        message = "Movie verified"
    else:
        message = "Invalid movie"
    return {"success": result, "detail": message}


@app.post("/recommend")
async def get_recommendations(seeds: Seeds, user_id: str = Depends(verify_jwt)):
    print('seeds', seeds)
    # recommend movies based on seeds
    message = recommender.recommend_movies(seeds.seeds)

    # save seeds
    success = bool(message)
    return {"success": success, "detail": message}


# setter: Create profile

# setter: Submit rating


# getter: Get profile

# getter: Get recommendations
