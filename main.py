from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return "Move Recommendations!"



git add .
git commit -m "Initial commit"