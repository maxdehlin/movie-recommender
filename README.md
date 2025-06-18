# movie-recommender


# TODO:
Update users to only include users which have accounts for databasing.

# Run locally
uvicorn app:app --reload --host 127.0.0.1 --port 8000
<!-- fastapi dev app.py -->


# Update code
fly deploy


# Dev site
https://movie-recommender-fragrant-shape-7289.fly.dev/


# start local sql
psql -U {user} -d movie_db

# start remote sql
psql postgresql://$REMOTE_POSTGRES_USER:$REMOTE_POSTGRES_PASSWORD@localhost:15432/movie_recommender_fragrant_shape_7289





# update sql tables with alembic
alembic revision --autogenerate -m "name of change"
alembic upgrade head


# attach app to database
fly postgres attach movierec-db --app movie-recommender-fragrant-shape-7289

# proxy
fly proxy 15432:5432 -a movierec-db

# restart db
fly machine list -a movierec-db
fly machine restart {machine} --a movierec-db


python3 -m venv .venv
source .venv/bin/activate
pip-compile requirements.in
pip install -r requirements.txt
