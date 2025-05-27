from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return "Move Recommendations!"


@app.get("/items")
async def items():
    return {"items": "Here are some movies you might like!"}


# setter: Create profile

# setter: Submit rating


# getter: Get profile

# getter: Get recommendations




