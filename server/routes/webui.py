from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from nonebot.log import logger

from server.pages.console_page import (
    render_console_page,
    render_groups_page,
    render_login_page,
    render_servers_page,
    render_shop_page,
    render_users_page,
    render_warehouse_page,
)
from server.routes import api_error, api_success, read_json_object
from server.server_config import WebServerSettings

router = APIRouter()

_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
WEBUI_STATIC_DIR = Path(__file__).resolve().parent.parent / "webui" / "static"


def _sanitize_next_path(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return "/webui"
    if not candidate.startswith("/"):
        return "/webui"
    if candidate.startswith("//"):
        return "/webui"
    return candidate


def _sign_payload(payload: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def _build_session_cookie(secret: str) -> str:
    issued_at = str(int(time.time()))
    signature = _sign_payload(issued_at, secret)
    raw = f"{issued_at}.{signature}".encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return encoded


def _decode_session_cookie(cookie_value: str) -> str | None:
    if not cookie_value:
        return None
    padding = "=" * ((4 - len(cookie_value) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode((cookie_value + padding).encode("ascii"))
    except Exception:
        return None
    decoded = raw.decode("utf-8", errors="ignore")
    return decoded if "." in decoded else None


def _verify_session_cookie(cookie_value: str, secret: str) -> bool:
    decoded = _decode_session_cookie(cookie_value)
    if decoded is None:
        return False

    issued_at_text, provided_signature = decoded.split(".", maxsplit=1)
    if not issued_at_text.isdigit():
        return False

    expected_signature = _sign_payload(issued_at_text, secret)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return False

    issued_at = int(issued_at_text)
    if int(time.time()) - issued_at > _SESSION_TTL_SECONDS:
        return False
    return True


def _is_authenticated(request: Request, settings: WebServerSettings) -> bool:
    cookie_value = request.cookies.get(settings.cookie_name, "")
    if cookie_value and _verify_session_cookie(cookie_value, settings.session_secret):
        return True
    query_token = request.query_params.get("token", "").strip()
    return bool(
        query_token and hmac.compare_digest(query_token, settings.webui_token)
    )


def _set_session_cookie(response: Response, settings: WebServerSettings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=_build_session_cookie(settings.session_secret),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=_SESSION_TTL_SECONDS,
    )


def add_webui_auth_middleware(app: FastAPI, settings: WebServerSettings) -> None:
    @app.middleware("http")
    async def _webui_auth_middleware(request: Request, call_next):
        path = request.url.path
        is_webui_auth_free_path = (
            path.startswith("/webui/login")
            or path.startswith("/webui/api/session")
            or path.startswith("/webui/static/")
        )
        if path.startswith("/webui") and not is_webui_auth_free_path:
            if not _is_authenticated(request, settings):
                next_path = path
                if request.url.query:
                    next_path = f"{next_path}?{request.url.query}"
                login_url = "/webui/login?" + urlencode({"next": next_path})
                return RedirectResponse(url=login_url, status_code=302)
        return await call_next(request)


def _resolve_webui_static_file(file_path: str) -> Path:
    resolved_path = (WEBUI_STATIC_DIR / file_path).resolve()
    try:
        resolved_path.relative_to(WEBUI_STATIC_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="forbidden") from exc
    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return resolved_path


def _get_settings_from_request(request: Request) -> WebServerSettings:
    return request.app.state.server_settings


@router.get("/webui", response_class=HTMLResponse)
async def webui_index(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_console_page())


@router.get("/webui/servers", response_class=HTMLResponse)
async def webui_servers_page(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_servers_page())


@router.get("/webui/users", response_class=HTMLResponse)
async def webui_users_page(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_users_page())


@router.get("/webui/groups", response_class=HTMLResponse)
async def webui_groups_page(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_groups_page())


@router.get("/webui/warehouse", response_class=HTMLResponse)
async def webui_warehouse_page(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_warehouse_page())


@router.get("/webui/shop", response_class=HTMLResponse)
async def webui_shop_page(request: Request) -> HTMLResponse:
    return HTMLResponse(content=render_shop_page())


@router.get("/webui/static/{file_path:path}")
async def webui_static(file_path: str) -> FileResponse:
    return FileResponse(path=_resolve_webui_static_file(file_path))


@router.get("/webui/login", response_class=HTMLResponse)
async def webui_login_page(request: Request) -> Response:
    settings = _get_settings_from_request(request)
    next_path = _sanitize_next_path(request.query_params.get("next"))
    if _is_authenticated(request, settings):
        return RedirectResponse(url=next_path, status_code=302)
    return HTMLResponse(content=render_login_page(next_path=next_path))


@router.post("/webui/api/session")
async def webui_session_create(request: Request) -> Response:
    settings = _get_settings_from_request(request)
    data, error_response = await read_json_object(request)
    if error_response is not None:
        return error_response
    assert data is not None

    provided_token = str(data.get("token", "")).strip()
    next_path = _sanitize_next_path(str(data.get("next", "")))

    if not provided_token:
        logger.warning("创建登录会话失败：reason=Token 不能为空")
        return api_error(
            status_code=422,
            code="validation_error",
            message="Token 不能为空",
            details=[{"field": "token", "message": "Token 不能为空"}],
        )

    if not hmac.compare_digest(provided_token, settings.webui_token):
        logger.warning("创建登录会话失败：reason=Token 错误")
        return api_error(
            status_code=401,
            code="unauthorized",
            message="Token 错误",
        )

    response = api_success(
        status_code=201,
        data={"next": next_path},
        headers={"Location": "/webui/api/session"},
    )
    _set_session_cookie(response, settings)
    logger.info("创建登录会话成功")
    return response


@router.delete("/webui/api/session")
async def webui_session_delete(request: Request) -> Response:
    settings = _get_settings_from_request(request)
    response = Response(status_code=204)
    response.delete_cookie(key=settings.cookie_name, path="/")
    logger.info("删除登录会话成功")
    return response
