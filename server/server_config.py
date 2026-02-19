from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass

from nonebot import get_driver


@dataclass(frozen=True)
class WebServerSettings:
    host: str
    port: int
    public_base_url: str
    webui_token: str
    webui_token_generated: bool
    session_secret: str
    session_secret_generated: bool
    cookie_name: str = "nextbot_webui_session"


_settings_lock = threading.Lock()
_cached_settings: WebServerSettings | None = None


def _parse_port(raw_value: object, default: int = 18081) -> int:
    try:
        port = int(raw_value)
    except (TypeError, ValueError):
        return default
    if 1 <= port <= 65535:
        return port
    return default


def _normalize_public_base_url(value: str, *, host: str, port: int) -> str:
    text = value.strip().rstrip("/")
    if text:
        return text
    return f"http://{host}:{port}"


def _build_settings() -> WebServerSettings:
    config = get_driver().config

    host = str(getattr(config, "WEB_SERVER_HOST", "127.0.0.1")).strip() or "127.0.0.1"
    port = _parse_port(getattr(config, "WEB_SERVER_PORT", 18081))
    public_base_url = _normalize_public_base_url(
        str(getattr(config, "WEB_SERVER_PUBLIC_BASE_URL", "")),
        host=host,
        port=port,
    )

    raw_token = str(getattr(config, "WEBUI_TOKEN", "")).strip()
    webui_token_generated = not raw_token
    webui_token = raw_token or secrets.token_urlsafe(24)

    raw_secret = str(getattr(config, "WEBUI_SESSION_SECRET", "")).strip()
    session_secret_generated = not raw_secret
    session_secret = raw_secret or secrets.token_urlsafe(32)

    return WebServerSettings(
        host=host,
        port=port,
        public_base_url=public_base_url,
        webui_token=webui_token,
        webui_token_generated=webui_token_generated,
        session_secret=session_secret,
        session_secret_generated=session_secret_generated,
    )


def get_server_settings() -> WebServerSettings:
    global _cached_settings
    with _settings_lock:
        if _cached_settings is None:
            _cached_settings = _build_settings()
        return _cached_settings
