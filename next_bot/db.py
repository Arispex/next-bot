from __future__ import annotations

from pathlib import Path

from sqlalchemy import String
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    ip: Mapped[str] = mapped_column(String, nullable=False)
    port: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)


def get_engine() -> Engine:
    return create_engine(
        DATABASE_URL,
        future=True,
        echo=False,
        connect_args={"check_same_thread": False},
    )


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
