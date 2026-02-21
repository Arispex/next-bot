from __future__ import annotations

import threading
from typing import Any

import uvicorn
from fastapi import FastAPI
from nonebot.log import logger

from server.page_store import create_page
from server.pages import inventory_page, progress_page
from server.routes.render import router as render_router
from server.routes.webui_commands import router as webui_commands_router
from server.routes.webui import add_webui_auth_middleware, router as webui_router
from server.server_config import WebServerSettings, get_server_settings

_server_started = False
_server_lock = threading.Lock()


def _build_internal_base_url(settings: WebServerSettings) -> str:
    return f"http://{settings.host}:{settings.port}"


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
    settings = get_server_settings()
    return f"{_build_internal_base_url(settings)}/render/inventory/{token}"


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
    settings = get_server_settings()
    return f"{_build_internal_base_url(settings)}/render/progress/{token}"


def create_app(settings: WebServerSettings | None = None) -> FastAPI:
    runtime_settings = settings or get_server_settings()

    app = FastAPI(
        title="NextBot Web Server",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.server_settings = runtime_settings

    add_webui_auth_middleware(app, runtime_settings)
    app.include_router(render_router)
    app.include_router(webui_router)
    app.include_router(webui_commands_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _run_server() -> None:
    settings = get_server_settings()
    app = create_app(settings)

    logger.info(f"Web Server 已启动：http://{settings.host}:{settings.port}")
    if settings.webui_token_generated:
        logger.warning("未配置 WEBUI_TOKEN，已自动生成临时 token：")
        logger.warning(settings.webui_token)
        logger.warning("可在 .env 中设置 WEBUI_TOKEN 以固定 token。")
    if settings.session_secret_generated:
        logger.info("未配置 WEBUI_SESSION_SECRET，已自动生成临时会话签名密钥。")

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )


def start_web_server() -> None:
    global _server_started
    with _server_lock:
        if _server_started:
            return
        thread = threading.Thread(
            target=_run_server,
            name="nextbot-web-server",
            daemon=True,
        )
        thread.start()
        _server_started = True


def start_render_server() -> None:
    # Backward compatible alias.
    start_web_server()
