from __future__ import annotations

from pathlib import Path

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ip: Mapped[str] = mapped_column(String, nullable=False)
    game_port: Mapped[str] = mapped_column(String, nullable=False)
    restapi_port: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    permissions: Mapped[str] = mapped_column(String, nullable=False, default="")
    group: Mapped[str] = mapped_column(String, nullable=False, default="guest")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class Group(Base):
    __tablename__ = "user_group"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    permissions: Mapped[str] = mapped_column(String, nullable=False, default="")
    inherits: Mapped[str] = mapped_column(String, nullable=False, default="")


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
    ensure_default_groups()


def get_session() -> Session:
    engine = get_engine()
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def ensure_default_groups() -> None:
    session = get_session()
    try:
        guest = session.query(Group).filter(Group.name == "guest").first()
        if guest is None:
            session.add(Group(name="guest", permissions="um.add", inherits=""))

        default = session.query(Group).filter(Group.name == "default").first()
        if default is None:
            session.add(
                Group(
                    name="default",
                    permissions="sm.*,gm.*,pm.*",
                    inherits="guest",
                )
            )
        session.commit()
    finally:
        session.close()
