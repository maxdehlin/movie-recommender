import os
from dotenv import load_dotenv
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/movie_db"
engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)

# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)