from pydantic import BaseModel


class User(BaseModel):
    loginname: str
    hashed_password: str