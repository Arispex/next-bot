from __future__ import annotations

import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from nonebot import get_driver
from nonebot.log import logger

from server.page_store import create_page, get_page
from server.pages import inventory_page, progress_page

BASE_DIR = Path(__file__).resolve().parent.parent
ITEMS_DIR = BASE_DIR / "server" / "assets" / "items"
DICTS_DIR = BASE_DIR / "server" / "assets" / "dicts"
_server_started = False
_server_lock = threading.Lock()


def _get_host() -> str:
    config = get_driver().config
    value = getattr(config, "RENDER_SERVER_HOST", "127.0.0.1")
    return str(value).strip() or "127.0.0.1"


def _get_port() -> int:
    config = get_driver().config
    value = getattr(config, "RENDER_SERVER_PORT", 18081)
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 18081
    if 1 <= port <= 65535:
        return port
    return 18081


def _build_base_url() -> str:
    return f"http://{_get_host()}:{_get_port()}"


def create_inventory_page(
    *,
    user_id: str,
    user_name: str,
    server_id: int,
    server_name: str,
    life_text: str,
    mana_text: str,
    fishing_tasks_text: str,
    pve_deaths_text: str,
    pvp_deaths_text: str,
    slots: list[dict[str, Any]],
) -> str:
    payload = inventory_page.build_payload(
        user_id=user_id,
        user_name=user_name,
        server_id=server_id,
        server_name=server_name,
        life_text=life_text,
        mana_text=mana_text,
        fishing_tasks_text=fishing_tasks_text,
        pve_deaths_text=pve_deaths_text,
        pvp_deaths_text=pvp_deaths_text,
        slots=slots,
    )
    token = create_page("inventory", payload)
    return f"{_build_base_url()}/inventory/{token}"


def create_progress_page(
    *,
    server_id: int,
    server_name: str,
    progress: dict[str, Any],
) -> str:
    payload = progress_page.build_payload(
        server_id=server_id,
        server_name=server_name,
        progress=progress,
    )
    token = create_page("progress", payload)
    return f"{_build_base_url()}/progress/{token}"


class _RenderRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/inventory/"):
            token = path.removeprefix("/inventory/").strip()
            self._handle_page(token, page_type="inventory", renderer=inventory_page.render)
            return
        if path.startswith("/progress/"):
            token = path.removeprefix("/progress/").strip()
            self._handle_page(token, page_type="progress", renderer=progress_page.render)
            return
        if path.startswith("/assets/items/"):
            self._handle_item_file(path)
            return
        if path.startswith("/assets/dicts/"):
            self._handle_dict_file(path)
            return
        if path == "/health":
            self._send_bytes(200, b"ok", "text/plain; charset=utf-8")
            return
        self._send_bytes(404, b"not found", "text/plain; charset=utf-8")

    def _handle_page(
        self,
        token: str,
        *,
        page_type: str,
        renderer: Any,
    ) -> None:
        payload = get_page(token)
        if payload is None or payload.get("type") != page_type:
            self._send_bytes(404, b"page not found", "text/plain; charset=utf-8")
            return
        try:
            content = renderer(payload)
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

    def _handle_dict_file(self, path: str) -> None:
        file_name = unquote(path.removeprefix("/assets/dicts/"))
        file_path = (DICTS_DIR / file_name).resolve()
        try:
            file_path.relative_to(DICTS_DIR.resolve())
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
