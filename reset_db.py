# reset_db.py
from recommender.models import Base
from recommender.db import engine
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
# print('database url', DATABASE_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)

# with engine.connect() as conn:
#     print('Dropping tables...')
#     conn.execute(text("DROP SCHEMA public CASCADE;"))
#     print('Creating tables...')
#     conn.execute(text("CREATE SCHEMA public;"))
Base.metadata.create_all(bind=engine)