from __future__ import annotations

import threading
import time
import uuid
from typing import Any

PAGE_EXPIRE_SECONDS = 600

_pages: dict[str, dict[str, Any]] = {}
_pages_lock = threading.Lock()


def _cleanup_expired_pages() -> None:
    now = time.time()
    expired_tokens = [
        token
        for token, payload in _pages.items()
        if now - float(payload.get("created_at_ts", now)) > PAGE_EXPIRE_SECONDS
    ]
    for token in expired_tokens:
        _pages.pop(token, None)


def create_page(page_type: str, payload: dict[str, Any]) -> str:
    token = uuid.uuid4().hex
    page_payload = dict(payload)
    page_payload["type"] = page_type
    page_payload["created_at_ts"] = time.time()
    with _pages_lock:
        _cleanup_expired_pages()
        _pages[token] = page_payload
    return token


def get_page(token: str) -> dict[str, Any] | None:
    with _pages_lock:
        _cleanup_expired_pages()
        return _pages.get(token)
