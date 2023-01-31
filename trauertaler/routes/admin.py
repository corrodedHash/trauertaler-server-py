import secrets

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from trauertaler import models
from trauertaler.database import get_db
from trauertaler.routes.login import pwd_context
from trauertaler.config import get_config, Config

app = FastAPI()

security = HTTPBasic()


def get_current_username(
    credentials: HTTPBasicCredentials = Depends(security),
    config: Config = Depends(get_config),
) -> str:
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = config.admin_pass.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


router = APIRouter()


class AddUserInfo(BaseModel):
    username: str
    password: str


@router.post("/add_user")
async def add_user(
    user: AddUserInfo,
    db: Session = Depends(get_db),
    credential: str = Depends(get_current_username),
) -> int:
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


class SetAmount(BaseModel):
    userid: str
    amount: int

    @validator("amount")
    def check_amount(cls, v: int) -> int:
        if v <= 0:
            raise HTTPException(400, "Amount must not be negative")
        return v


@router.post("/set_amount")
async def set_amount(
    info: SetAmount,
    db: Session = Depends(get_db),
    credential: str = Depends(get_current_username),
) -> int:
    eu = db.query(models.Ledger).filter(models.Ledger.id == info.userid).first()
    if eu is None:
        raise HTTPException(400, "User does not exists")
    eu.amount = info.amount
    db.commit()
    db.refresh(eu)
    return eu.amount
