from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import nonebot
from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot as OBV11Bot
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger

from nextbot.access_control import get_group_ids
from nextbot.db import User, get_session
from server.routes import api_error, api_success, read_json_object

router = APIRouter()


def _pick_onebot_bot() -> OBV11Bot | None:
    for bot in get_bots().values():
        if isinstance(bot, OBV11Bot):
            return bot
    return None


def _resolve_user_id_by_name(name: str) -> str | None:
    session = get_session()
    try:
        user = session.query(User).filter(User.name == name).order_by(User.id.asc()).first()
        return str(user.user_id) if user is not None else None
    finally:
        session.close()


async def _find_user_group(bot: OBV11Bot, user_id: str) -> int | None:
    allowed_groups = get_group_ids()
    if not allowed_groups:
        return None

    for raw_gid in allowed_groups:
        try:
            group_id = int(raw_gid)
        except (TypeError, ValueError):
            continue
        try:
            await bot.call_api(
                "get_group_member_info",
                group_id=group_id,
                user_id=int(user_id),
                no_cache=False,
            )
        except Exception:
            continue
        return group_id
    return None


async def _find_all_user_groups(bot: OBV11Bot, user_id: str) -> list[int]:
    allowed_groups = get_group_ids()
    if not allowed_groups:
        return []

    found: list[int] = []
    for raw_gid in allowed_groups:
        try:
            group_id = int(raw_gid)
        except (TypeError, ValueError):
            continue
        try:
            await bot.call_api(
                "get_group_member_info",
                group_id=group_id,
                user_id=int(user_id),
                no_cache=False,
            )
        except Exception:
            continue
        found.append(group_id)
    return found


@router.post("/webui/api/login-requests")
async def webui_login_requests_create(request: Request) -> JSONResponse:
    data, error_response = await read_json_object(request)
    if error_response is not None:
        return error_response
    assert data is not None

    name = str(data.get("name") or "").strip()
    if not name:
        return api_error(
            status_code=422,
            code="validation_error",
            message="用户名称不能为空",
            details=[{"field": "name", "message": "用户名称不能为空"}],
        )

    new_device = bool(data.get("newDevice", False))
    new_location = bool(data.get("newLocation", False))

    user_id = _resolve_user_id_by_name(name)
    if user_id is None:
        logger.warning(f"发送登入确认失败：name={name}，reason=用户不存在")
        return api_error(
            status_code=404,
            code="not_found",
            message="用户不存在",
        )

    bot = _pick_onebot_bot()
    if bot is None:
        logger.warning(
            f"发送登入确认失败：name={name}，user_id={user_id}，reason=机器人未连接"
        )
        return api_error(
            status_code=503,
            code="bot_unavailable",
            message="机器人未连接",
        )

    config = nonebot.get_driver().config
    notify_all = bool(getattr(config, "login_notify_all_groups", False))

    if notify_all:
        group_ids = await _find_all_user_groups(bot, user_id)
    else:
        first = await _find_user_group(bot, user_id)
        group_ids = [first] if first is not None else []

    if not group_ids:
        logger.warning(
            f"发送登入确认失败：name={name}，user_id={user_id}，reason=未在任何群中找到该用户"
        )
        return api_error(
            status_code=404,
            code="group_not_found",
            message="未在任何群中找到该用户",
        )

    if new_device and new_location:
        change_text = "有新设备在新地点正在尝试登入服务器"
    elif new_device:
        change_text = "有新设备正在尝试登入服务器"
    elif new_location:
        change_text = "在新地点正在尝试登入服务器"
    else:
        change_text = "有新设备或者在新地点正在尝试登入服务器"

    message: list[Any] = [
        OBV11MessageSegment.at(int(user_id)),
        OBV11MessageSegment.text(
            f"\n{change_text}\n请回复「允许登入」或「拒绝登入」\n该请求 5 分钟内有效"
        ),
    ]

    results: list[dict[str, Any]] = []
    for gid in group_ids:
        try:
            send_result = await bot.call_api(
                "send_group_msg",
                group_id=gid,
                message=message,
            )
        except Exception as exc:
            logger.exception(
                f"发送登入确认异常：name={name}，user_id={user_id}，group_id={gid}，reason={exc}"
            )
            results.append({"group_id": gid, "message_id": None})
            continue

        msg_id: int | None = None
        if isinstance(send_result, dict):
            raw_msg_id = send_result.get("message_id")
            if isinstance(raw_msg_id, int):
                msg_id = raw_msg_id

        logger.info(
            f"发送登入确认成功：name={name}，user_id={user_id}，group_id={gid}，message_id={msg_id}"
        )
        results.append({"group_id": gid, "message_id": msg_id})

    if not any(r["message_id"] is not None for r in results):
        return api_error(
            status_code=502,
            code="send_failed",
            message="发送消息失败",
        )

    if len(results) == 1:
        return api_success(
            status_code=201,
            data={
                "name": name,
                "user_id": user_id,
                "group_id": results[0]["group_id"],
                "message_id": results[0]["message_id"],
            },
        )

    return api_success(
        status_code=201,
        data={
            "name": name,
            "user_id": user_id,
            "results": results,
        },
    )
