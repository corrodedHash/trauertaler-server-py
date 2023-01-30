from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from trauertaler import models
from trauertaler.database import get_db
from trauertaler.routes.login import get_current_user_id


router = APIRouter()


class Transaction(BaseModel):
    sender_id: str
    receiver_id: str
    amount: int
    sendtime: datetime


class AddTransaction(BaseModel):
    receiver_id: str
    amount: int

    @validator("amount")
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


@router.get("/ledger")
async def get_amount(
    userid: int = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> int:
    print(userid)
    l = db.query(models.Ledger).filter(models.Ledger.owner_id == userid).first()
    if l is None:
        raise HTTPException(400, "Unknown user")
    return l.amount


websockets: dict[int, list[WebSocket]] = {}


@router.post("/transactions", response_model=Transaction)
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
        sender_id=userid,
        receiver_id=r.owner_id,
        sendtime=datetime.utcnow(),
        amount=transaction.amount,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    send_futures = [
        ws.send_json(
            {
                "sender": t.sender_id,
                "receiver": t.receiver_id,
                "sendtime": t.sendtime,
                "amount": t.amount,
            }
        )
        for ws in websockets.get(t.sender_id, list())
        + websockets.get(t.receiver_id, list())
    ]
    for f in send_futures:
        await f

    return t


@router.get("/transactions", response_model=list[Transaction])
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

@router.websocket("/subscribe")
async def websocket_endpoint(
    websocket: WebSocket,
    userid: int = Depends(get_current_user_id),
) -> None:
    await websocket.accept()
    websockets.get(userid, list())
    try:
        pass
    except WebSocketDisconnect:
        pass