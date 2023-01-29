from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    loginname: str
    hashed_password: str


class Transaction(BaseModel):
    sender_id: str
    receiver_id: str
    amount: int
    sendtime: datetime
