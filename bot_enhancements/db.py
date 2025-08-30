from __future__ import annotations
from sqlalchemy import create_engine, text, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship, sessionmaker
from datetime import datetime
import os

class Base(DeclarativeBase): 
    pass

class Trade(Base):
    __tablename__ = 'trades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    order_id: Mapped[str] = mapped_column(String(64))
    meta: Mapped[dict] = mapped_column(JSON, default={})

class Lot(Base):
    __tablename__ = 'lots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String(16))
    qty: Mapped[float] = mapped_column(Float)  # remaining qty
    cost_basis: Mapped[float] = mapped_column(Float)  # per unit in USD
    acquired: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lot_tag: Mapped[str] = mapped_column(String(64), default='')

class Realized(Base):
    __tablename__ = 'realized'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String(16))
    qty: Mapped[float] = mapped_column(Float)
    proceeds: Mapped[float] = mapped_column(Float)
    basis: Mapped[float] = mapped_column(Float)
    gain: Mapped[float] = mapped_column(Float)
    short_term: Mapped[bool] = mapped_column(Boolean)
    opened: Mapped[datetime] = mapped_column(DateTime)
    closed: Mapped[datetime] = mapped_column(DateTime)
    lot_ids: Mapped[str] = mapped_column(String(256))

class Settings(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512))
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Metric(Base):
    __tablename__ = 'metrics'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def engine_and_session(url: str | None = None):
    url = url or os.getenv('DATABASE_URL', 'postgresql+psycopg2://user:pass@localhost:5432/cryptobot')
    eng = create_engine(url, future=True)
    Session = sessionmaker(eng, expire_on_commit=False)
    return eng, Session

def migrate(url: str | None = None):
    eng, _ = engine_and_session(url)
    Base.metadata.create_all(eng)