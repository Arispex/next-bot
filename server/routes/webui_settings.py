from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from server.pages.console_page import render_settings_page
from server.settings_service import (
    SettingsValidationError,
    get_settings_metadata,
    get_settings_snapshot,
    save_settings,
)

router = APIRouter()


@router.get("/webui/settings", response_class=HTMLResponse)
async def webui_settings_page() -> HTMLResponse:
    return HTMLResponse(content=render_settings_page())


@router.get("/webui/api/settings")
async def webui_settings_get() -> JSONResponse:
    return JSONResponse(
        content={
            "ok": True,
            "data": get_settings_snapshot(),
            "meta": get_settings_metadata(),
        }
    )


@router.put("/webui/api/settings")
async def webui_settings_put(request: Request) -> JSONResponse:
    try:
        payload: Any = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "请求体必须是 JSON"},
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "请求体必须是对象"},
        )

    data = payload.get("data")
    if data is None:
        data = payload
    if not isinstance(data, dict):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "data 必须是对象"},
        )

    try:
        result = save_settings(data)
    except SettingsValidationError as exc:
        content: dict[str, Any] = {"ok": False, "message": str(exc)}
        if exc.field:
            content["field"] = exc.field
        return JSONResponse(status_code=422, content=content)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"保存失败：{exc}"},
        )

    return JSONResponse(
        content={
            "ok": True,
            "message": "保存成功",
            "applied_now_fields": result.applied_now_fields,
            "restart_required_fields": result.restart_required_fields,
        }
    )
