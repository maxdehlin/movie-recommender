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
from recommender.db import insert_user
from recommender.models import User
from recommender.recommender import verify_movie_in_db, recommend_movies
from schemas import Seeds
# Load environment variables from a “.env” file 
config = Config(".env")

client_id = os.getenv("DEV_GOOGLE_CLIENT_ID")
client_secret = os.getenv("DEV_GOOGLE_CLIENT_SECRET")




load_dotenv()
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
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET") or "some‐random-string",
)

@app.get("/auth/google/login")
async def google_login(request: Request):
    """
    Redirect single-page frontend (or any client) to Google’s consent screen.
    """
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
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
    
    user = insert_user(google_id, email, name)

    # generate a JWT so the frontend can call protected APIs
    expire = int(time.time() + JWT_EXPIRE_SECONDS)
    payload = {
        "sub": str(user.id),
        "exp": expire,
    }
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/verify_movie")
async def verify_movie(
    movie: str
):
    # print(movie)
    result = verify_movie_in_db(movie)
    if result:
        message = "Movie verified"
    else:
        message = "Invalid movie"
    return {"success": result, "detail": message}



@app.post("/recommend")
async def get_recommendations(seeds: Seeds):
    print(seeds)
    message = recommend_movies(seeds.seeds)
    success = bool(message)
    return {"success": success, "detail": message}


# setter: Create profile

# setter: Submit rating


# getter: Get profile

# getter: Get recommendations
