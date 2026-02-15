from __future__ import annotations

import json
import mimetypes
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from nonebot import get_driver
from nonebot.log import logger

BASE_DIR = Path(__file__).resolve().parent.parent
ITEMS_DIR = BASE_DIR / "assets" / "items"
TEMPLATES_DIR = BASE_DIR / "server" / "templates"
INVENTORY_TEMPLATE_PATH = TEMPLATES_DIR / "inventory.html"
PAGE_EXPIRE_SECONDS = 600

_inventory_pages: dict[str, dict[str, Any]] = {}
_inventory_lock = threading.Lock()
_server_started = False
_server_lock = threading.Lock()


def _get_host() -> str:
    config = get_driver().config
    return str(getattr(config, "render_server_host", "127.0.0.1")).strip() or "127.0.0.1"


def _get_port() -> int:
    config = get_driver().config
    value = getattr(config, "render_server_port", 18081)
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 18081
    if 1 <= port <= 65535:
        return port
    return 18081


def _build_base_url() -> str:
    return f"http://{_get_host()}:{_get_port()}"


def _cleanup_expired_pages() -> None:
    now = time.time()
    expired_tokens = [
        token
        for token, payload in _inventory_pages.items()
        if now - float(payload.get("created_at_ts", now)) > PAGE_EXPIRE_SECONDS
    ]
    for token in expired_tokens:
        _inventory_pages.pop(token, None)


def _normalize_inventory_slots(slots: list[dict[str, Any]]) -> list[dict[str, int]]:
    normalized: list[dict[str, int]] = []
    for index in range(350):
        net_id = 0
        stack = 0
        if index < len(slots) and isinstance(slots[index], dict):
            raw_net_id = slots[index].get("netID", 0)
            raw_stack = slots[index].get("stack", 0)
            try:
                net_id = int(raw_net_id)
            except (TypeError, ValueError):
                net_id = 0
            try:
                stack = int(raw_stack)
            except (TypeError, ValueError):
                stack = 0
        normalized.append({"net_id": max(net_id, 0), "stack": max(stack, 0)})
    return normalized


def create_inventory_page(
    *,
    user_id: str,
    user_name: str,
    server_id: int,
    server_name: str,
    slots: list[dict[str, Any]],
) -> str:
    token = uuid.uuid4().hex
    payload = {
        "created_at_ts": time.time(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": str(user_id),
        "user_name": str(user_name),
        "server_id": str(server_id),
        "server_name": str(server_name),
        "slots": _normalize_inventory_slots(slots),
    }
    with _inventory_lock:
        _cleanup_expired_pages()
        _inventory_pages[token] = payload
    return f"{_build_base_url()}/inventory/{token}"


def _render_inventory_page(payload: dict[str, Any]) -> bytes:
    template = INVENTORY_TEMPLATE_PATH.read_text(encoding="utf-8")
    data = {
        "user_id": payload.get("user_id", ""),
        "user_name": payload.get("user_name", ""),
        "server_id": payload.get("server_id", ""),
        "server_name": payload.get("server_name", ""),
        "generated_at": payload.get("generated_at", ""),
        "slots": payload.get("slots", []),
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    content = template.replace("__INVENTORY_DATA_JSON__", data_json)
    return content.encode("utf-8")


class _RenderRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/inventory/"):
            token = path.removeprefix("/inventory/").strip()
            self._handle_inventory(token)
            return
        if path.startswith("/assets/items/"):
            self._handle_item_file(path)
            return
        if path == "/health":
            self._send_bytes(200, b"ok", "text/plain; charset=utf-8")
            return
        self._send_bytes(404, b"not found", "text/plain; charset=utf-8")

    def _handle_inventory(self, token: str) -> None:
        with _inventory_lock:
            payload = _inventory_pages.get(token)
        if payload is None:
            self._send_bytes(404, b"page not found", "text/plain; charset=utf-8")
            return
        try:
            content = _render_inventory_page(payload)
        except OSError:
            self._send_bytes(500, b"template read error", "text/plain; charset=utf-8")
            return
        self._send_bytes(200, content, "text/html; charset=utf-8")

    def _handle_item_file(self, path: str) -> None:
        file_name = unquote(path.removeprefix("/assets/items/"))
        file_path = (ITEMS_DIR / file_name).resolve()
        try:
            file_path.relative_to(ITEMS_DIR.resolve())
        except ValueError:
            self._send_bytes(403, b"forbidden", "text/plain; charset=utf-8")
            return
        if not file_path.is_file():
            self._send_bytes(404, b"not found", "text/plain; charset=utf-8")
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self._send_bytes(200, file_path.read_bytes(), content_type)

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _run_server() -> None:
    host = _get_host()
    port = _get_port()
    httpd = ThreadingHTTPServer((host, port), _RenderRequestHandler)
    logger.info(f"渲染 Web Server 已启动：http://{host}:{port}")
    httpd.serve_forever()


def start_render_server() -> None:
    global _server_started
    with _server_lock:
        if _server_started:
            return
        thread = threading.Thread(target=_run_server, name="render-web-server", daemon=True)
        thread.start()
        _server_started = True
