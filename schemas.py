from pydantic import BaseModel, constr

# what client sends us
class ProfileCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=8)


# what we return
class ProfileRead(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Seed(BaseModel):
    title: str
    rating: float


class Seeds(BaseModel):
    seeds: list[Seed]


class RatingRequest(BaseModel):
    movie: str
    value: int