# movie-recommender

# Run locally
uvicorn app:app --reload --host 127.0.0.1 --port 8000
<!-- fastapi dev app.py -->


# Update code
fly deploy


# Dev site
https://movie-recommender-fragrant-shape-7289.fly.dev/


# start sql
psql -U {user} -d movie_db



# update sql tables with alembic
alembic revision --autogenerate -m "name of change"
alembic upgrade head
