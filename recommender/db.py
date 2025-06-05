import os
from dotenv import load_dotenv
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from recommender.models import Base
from sqlalchemy.ext.declarative import declarative_base

url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/movie_db"
engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()