from fastapi import FastAPI
# from sqlalchemy.orm import Session

import schemas
# from .utils.security import hash_password



app = FastAPI()


@app.get("/")
async def root():
    return "Move Recommendations!"


@app.get("/items")
async def items():
    return {"items": "Here are some movies you might like!"}


@app.post("/profiles")
async def create_profile(
    in_profile: schemas.ProfileCreate
):
    return {"success": True, "detail": "Profile created successfully."}


@app.get("/verify_movie")
async def create_profile(
    in_profile: schemas.ProfileCreate
):
    return {"success": True, "detail": "Profile created successfully."}


# setter: Create profile

# setter: Submit rating


# getter: Get profile

# getter: Get recommendations
