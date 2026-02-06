from __future__ import annotations

from typing import Iterable

from nonebot import get_driver
from nonebot.log import logger

from next_bot.db import Group, User, get_session


def _split_values(value: str) -> list[str]:
    return [item for item in (v.strip() for v in value.split(",")) if item]


def _join_values(values: Iterable[str]) -> str:
    return ",".join(sorted(set(values)))


def _match_permission(granted: str, required: str) -> bool:
    if granted.endswith(".*"):
        prefix = granted[:-1]
        return required.startswith(prefix)
    return granted == required


def get_effective_permissions(user_id: str) -> set[str]:
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            group_name = "guest"
            user_perms: set[str] = set()
        else:
            group_name = user.group or "guest"
            user_perms = set(_split_values(user.permissions))

        group_perms = _get_group_permissions(session, group_name, set())
        return user_perms | group_perms
    finally:
        session.close()


def _get_group_permissions(
    session,
    group_name: str,
    visited: set[str],
) -> set[str]:
    if group_name in visited:
        return set()
    visited.add(group_name)

    group = session.query(Group).filter(Group.name == group_name).first()
    if group is None:
        return set()

    perms = set(_split_values(group.permissions))
    for parent in _split_values(group.inherits):
        perms |= _get_group_permissions(session, parent, visited)
    return perms


def _get_owner_id() -> str:
    config = get_driver().config
    owner_id = getattr(config, "owner_id", "")
    return str(owner_id).strip() if owner_id is not None else ""


def has_permission(user_id: str, permission: str) -> bool:
    owner_id = _get_owner_id()
    if owner_id and user_id == owner_id:
        return True
    perms = get_effective_permissions(user_id)
    return any(_match_permission(granted, permission) for granted in perms)


def require_permission(permission: str):
    def decorator(func):
        import inspect
        from functools import wraps

        signature = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            bound = signature.bind_partial(*args, **kwargs)
            bot = bound.arguments.get("bot")
            event = bound.arguments.get("event")
            if bot is None or event is None:
                return await func(*args, **kwargs)

            user_id = event.get_user_id()
            if not has_permission(user_id, permission):
                logger.info(
                    f"权限不足：user_id={user_id} permission={permission}"
                )
                await bot.send(event, "没有权限")
                return
            return await func(*args, **kwargs)

        wrapper.__signature__ = signature
        return wrapper

    return decorator


def add_permission(value: str, permission: str) -> str:
    perms = set(_split_values(value))
    perms.add(permission)
    return _join_values(perms)


def remove_permission(value: str, permission: str) -> str:
    perms = set(_split_values(value))
    perms.discard(permission)
    return _join_values(perms)


def add_inherit(value: str, parent: str) -> str:
    parents = set(_split_values(value))
    parents.add(parent)
    return _join_values(parents)


def remove_inherit(value: str, parent: str) -> str:
    parents = set(_split_values(value))
    parents.discard(parent)
    return _join_values(parents)
