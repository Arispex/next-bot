from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert

from next_bot.db import Server, SystemStat, User, get_engine, get_session

STAT_COMMAND_EXECUTE_TOTAL = "command.execute.total"


def increment_stat(stat_key: str, delta: int = 1) -> None:
    key = str(stat_key).strip()
    if not key:
        return

    amount = int(delta)
    if amount == 0:
        return

    now = datetime.utcnow()
    engine = get_engine()

    with engine.begin() as connection:
        statement = insert(SystemStat).values(
            stat_key=key,
            stat_value=amount,
            updated_at=now,
        )
        upsert = statement.on_conflict_do_update(
            index_elements=[SystemStat.stat_key],
            set_={
                "stat_value": SystemStat.stat_value + amount,
                "updated_at": now,
            },
        )
        connection.execute(upsert)


def get_stat_value(stat_key: str, default: int = 0) -> int:
    key = str(stat_key).strip()
    if not key:
        return int(default)

    session = get_session()
    try:
        row = session.query(SystemStat).filter(SystemStat.stat_key == key).first()
        if row is None:
            return int(default)
        return int(row.stat_value)
    finally:
        session.close()


def increment_command_execute_total() -> None:
    increment_stat(STAT_COMMAND_EXECUTE_TOTAL, 1)


def get_dashboard_metrics() -> dict[str, int | str]:
    session = get_session()
    try:
        server_count = int(session.query(func.count(Server.id)).scalar() or 0)
        user_count = int(session.query(func.count(User.id)).scalar() or 0)
    finally:
        session.close()

    return {
        "running_status": "Running",
        "server_count": server_count,
        "user_count": user_count,
        "command_execute_count": get_stat_value(STAT_COMMAND_EXECUTE_TOTAL, 0),
    }
