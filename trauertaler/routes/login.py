from datetime import datetime, timedelta

import jwt
from fastapi import Depends, APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from trauertaler.config import Config, get_config
from .. import models

from ..database import get_db


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, str | datetime],
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)

    return encoded_jwt


def get_userid_from_jwt(token: str, key: str, algorithm: str) -> str | None:
    payload = jwt.decode(token, key, algorithms=[algorithm])
    return payload.get("sub")


async def get_current_user_id(
    token: str = Depends(oauth2_scheme), config: Config = Depends(get_config)
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        userid = get_userid_from_jwt(
            token, config.secret_key, algorithm=config.algorithm
        )
        if userid is None:
            raise credentials_exception
        return userid
    except:
        raise credentials_exception


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    config: Config = Depends(get_config),
) -> dict[str, str]:
    user = (
        db.query(models.User)
        .filter(models.User.loginname == form_data.username.lower())
        .first()
    )
    login_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if user is None:
        raise login_exception
    check = pwd_context.verify(form_data.password, str(user.hashed_password))
    if not check:
        raise login_exception
    access_token_expires = timedelta(minutes=config.access_token_exprire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
        secret_key=config.secret_key,
        algorithm=config.algorithm,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/username/{uuid}")
async def get_username(uuid: str, db: Session = Depends(get_db)) -> str:
    u = db.query(models.User).filter(models.User.id == uuid).first()
    if u is None:
        raise HTTPException(400, "Unknown id")
    return str(u.loginname)


@router.get("/uuid/{username}")
async def get_uuid(username: str, db: Session = Depends(get_db)) -> str:
    u = db.query(models.User).filter(models.User.loginname == username.lower()).first()
    if u is None:
        raise HTTPException(400, "Unknown username")
    return str(u.id)
