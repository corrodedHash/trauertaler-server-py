from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import database, login, models, schemas
from .database import get_db
from .login import get_current_user_id, pwd_context

from sqlalchemy import MetaData
from .database import engine

meta_data = MetaData()

app = FastAPI()
app.include_router(login.router)


models.Base.metadata.create_all(bind=engine)


class AddUserInfo(BaseModel):
    username: str
    password: str


class AddTransaction(BaseModel):
    receiver_id: str
    amount: int


@app.post("/api/admin/add_user", include_in_schema=False)
async def add_user(user: AddUserInfo, db: Session = Depends(get_db)):
    eu = (
        db.query(models.User)
        .filter(models.User.loginname == user.username.lower())
        .count()
    )
    if eu > 0:
        raise HTTPException(400, "User exists")
    u = models.User(
        loginname=user.username.lower(), hashed_password=pwd_context.hash(user.password)
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    l = models.Ledger(owner_id=u.id, amount=0)
    db.add(l)
    db.commit()
    return u.id


@app.get("/api/username/{uuid}")
async def get_username(uuid: str, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == uuid).first()
    if u is None:
        raise HTTPException(400, "Unknown id")
    return u.username


@app.get("/api/uuid/{username}")
async def get_uuid(username: str, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.loginname == username.lower()).first()
    if u is None:
        raise HTTPException(400, "Unknown username")
    return u.username


@app.get("/api/ledger")
async def get_amount(
    userid=Depends(get_current_user_id), db: Session = Depends(get_db)
):
    print(userid)
    l = db.query(models.Ledger).filter(models.Ledger.owner_id == userid).first()
    if l is None:
        raise HTTPException(400, "Unknown user")
    return l.amount


@app.post("/api/transactions")
async def set_transaction(
    transaction: AddTransaction,
    userid=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if transaction.amount <= 0:
        raise HTTPException(400, "Transaction amount non-positive")
    l = db.query(models.Ledger).filter(models.Ledger.owner_id == userid).first()
    if l is None:
        raise HTTPException(400, "Unknown user")

    if l.amount < transaction.amount:
        raise HTTPException(401, "Too little funds")

    r = (
        db.query(models.Ledger)
        .filter(models.Ledger.owner_id == transaction.receiver_id)
        .first()
    )
    if r is None:
        raise HTTPException(402, "Unknown receiver")
    l.update({"amount": l.amount - transaction.amount})
    r.update({"amount": r.amount + transaction.amount})
    t = models.Transactions(
        sender_id=userid, receiver_id=r.owner_id, sendtime=datetime.utcnow()
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@app.get("/api/transactions")
async def get_transaction(
    userid=Depends(get_current_user_id), skip: int = 0, limit: int = 10
):
    limit = min(limit, 10)
    if limit < 0:
        limit = 10
    return {}
