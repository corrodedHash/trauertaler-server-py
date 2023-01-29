from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    loginname = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True)
    amount = Column(Integer, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)


class Transactions(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    sendtime = Column(Integer, nullable=False)
