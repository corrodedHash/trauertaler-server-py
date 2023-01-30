from sqlalchemy import ForeignKey
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base as Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    loginname: Mapped[str] = mapped_column(
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column()


class Ledger(Base):
    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    amount: Mapped[int] = mapped_column()


class Transactions(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    receiver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    sendtime: Mapped[datetime] = mapped_column()
