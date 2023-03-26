from datetime import datetime, timedelta

import jwt
import sqlalchemy.sql
from fastapi import APIRouter, Depends, HTTPException, status
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


def create_token(db: Session, config: Config, userid: str) -> Token:
    def create_access_token(
        data: dict[str, str | datetime],
        timestamp: datetime,
        secret_key: str,
        algorithm: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        to_encode = data.copy()
        if expires_delta is None:
            expires_delta = timedelta(minutes=15)
        expire = timestamp + expires_delta

        to_encode.update({"exp": str(expire)})
        to_encode.update({"iss": str(timestamp)})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)

        return encoded_jwt

    access_token_expires = timedelta(minutes=config.access_token_exprire_minutes)
    maybe_timestamp = db.query(sqlalchemy.sql.func.now()).first()
    if maybe_timestamp is None:
        raise HTTPException(500, "Could not get server timestamp")

    access_token = create_access_token(
        data={"sub": userid},
        expires_delta=access_token_expires,
        timestamp=maybe_timestamp[0],
        secret_key=config.secret_key,
        algorithm=config.algorithm,
    )

    return Token.parse_obj({"access_token": access_token, "token_type": "bearer"})


def get_userid_from_jwt(
    token: str, key: str, algorithm: str, db: Session
) -> str | None:
    payload = jwt.decode(token, key, algorithms=[algorithm])
    expiry_date_str = payload.get("exp")
    if expiry_date_str is None:
        return None
    expiry_date = datetime.strptime(expiry_date_str, "%m/%d/%y %H:%M:%S.%f")

    issue_date_str = payload.get("iss")
    if issue_date_str is None:
        return None
    issue_date = datetime.strptime(issue_date_str, "%m/%d/%y %H:%M:%S.%f")

    now_timestamp_maybe = db.query(sqlalchemy.sql.func.now()).first()
    assert now_timestamp_maybe is not None
    now_timestamp: datetime = now_timestamp_maybe[0]
    if expiry_date < now_timestamp:
        return None
    userid = payload.get("sub")
    if userid is None:
        return None

    last_change_time_maybe = (
        db.query(models.User.last_password_change)
        .filter(models.User.id == userid)
        .first()
    )
    if last_change_time_maybe is None:
        return None
    last_change_time = last_change_time_maybe[0]

    if issue_date < last_change_time:
        return None

    return str(userid)


async def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    config: Config = Depends(get_config),
    db: Session = Depends(get_db),
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        userid = get_userid_from_jwt(
            token, config.secret_key, algorithm=config.algorithm, db=db
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
) -> Token:
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
    access_token = create_token(db, config, str(user.id))
    return access_token


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


@router.post("/password")
async def change_password(
    password: str,
    userid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    config: Config = Depends(get_config),
) -> Token:
    u = db.query(models.User).filter(models.User.id == userid).first()
    if u is None:
        raise HTTPException(400, "User unknown")
    u.hashed_password = get_password_hash(password)
    db.commit()

    return create_token(db, config, userid)
