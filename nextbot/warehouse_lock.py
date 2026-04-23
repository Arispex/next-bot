from __future__ import annotations

import asyncio

# Per-user warehouse lock shared across the bot plugin and the WebUI API.
# Acquire before any read-modify-write on a single user's WarehouseItem rows
# so concurrent claim / recycle / drop / remove / add (from chat OR WebUI)
# can't race past each other's snapshots.
_WAREHOUSE_LOCKS: dict[str, asyncio.Lock] = {}


def warehouse_lock(user_id: str) -> asyncio.Lock:
    lock = _WAREHOUSE_LOCKS.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _WAREHOUSE_LOCKS[user_id] = lock
    return lock
