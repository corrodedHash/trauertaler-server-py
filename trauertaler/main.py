from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from . import database, login, models, schemas
from .database import get_db
from .login import get_current_user_id, pwd_context

from sqlalchemy import MetaData
from .database import engine

meta_data = MetaData()

app = FastAPI(root_path="/api")
app.include_router(login.router)


database.Base.metadata.create_all(bind=engine)


class AddUserInfo(BaseModel):
    username: str
    password: str


class AddTransaction(BaseModel):
    receiver_id: str
    amount: int

    @validator("amount")
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


@app.post("/admin/add_user", include_in_schema=False)
async def add_user(user: AddUserInfo, db: Session = Depends(get_db)) -> int:
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


@app.get("/username/{uuid}")
async def get_username(uuid: str, db: Session = Depends(get_db)) -> str:
    u = db.query(models.User).filter(models.User.id == uuid).first()
    if u is None:
        raise HTTPException(400, "Unknown id")
    return str(u.loginname)


@app.get("/uuid/{username}")
async def get_uuid(username: str, db: Session = Depends(get_db)) -> str:
    u = db.query(models.User).filter(models.User.loginname == username.lower()).first()
    if u is None:
        raise HTTPException(400, "Unknown username")
    return str(u.loginname)


@app.get("/ledger")
async def get_amount(
    userid: int = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> int:
    print(userid)
    l = db.query(models.Ledger).filter(models.Ledger.owner_id == userid).first()
    if l is None:
        raise HTTPException(400, "Unknown user")
    return l.amount


@app.post("/transactions", response_model=schemas.Transaction)
async def set_transaction(
    transaction: AddTransaction,
    userid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> models.Transactions:
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
    l.amount -= transaction.amount
    r.amount += transaction.amount
    t = models.Transactions(
        sender_id=userid, receiver_id=r.owner_id, sendtime=datetime.utcnow()
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@app.get("/transactions")
async def get_transaction(
    userid: int = Depends(get_current_user_id),
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> list[models.Transactions]:
    limit = min(limit, 10)
    if limit < 0:
        limit = 10
    l = (
        db.query(models.Transactions)
        .filter(models.Transactions.id == userid)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return l
