from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import nonebot
from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot as OBV11Bot
from nonebot.log import logger

from sqlalchemy import func

from nextbot.access_control import get_group_ids
from nextbot.db import User, get_session
from server.routes import api_error, api_success, read_json_object

router = APIRouter()

_ALLOWED_EVENTS = {"online", "offline"}


def _pick_onebot_bot() -> OBV11Bot | None:
    for bot in get_bots().values():
        if isinstance(bot, OBV11Bot):
            return bot
    return None


def _resolve_user_id_by_name(name: str) -> str | None:
    session = get_session()
    try:
        user = (
            session.query(User)
            .filter(func.lower(User.name) == name.lower())
            .order_by(User.id.asc())
            .first()
        )
        return str(user.user_id) if user is not None else None
    finally:
        session.close()


def _resolve_target_groups() -> list[int]:
    config = nonebot.get_driver().config
    mode = str(getattr(config, "player_notify_mode", "all") or "").strip().lower()
    single_gid = str(getattr(config, "player_notify_group_id", "") or "").strip()

    if mode == "single":
        if single_gid.isdigit():
            return [int(single_gid)]
        return []

    target: list[int] = []
    for raw_gid in get_group_ids():
        text = str(raw_gid).strip()
        if text.isdigit():
            target.append(int(text))
    return target


@router.post("/webui/api/player-events")
async def webui_player_events_create(request: Request) -> JSONResponse:
    data, error_response = await read_json_object(request)
    if error_response is not None:
        return error_response
    assert data is not None

    player_name = str(data.get("player_name") or "").strip()
    if not player_name:
        return api_error(
            status_code=422,
            code="validation_error",
            message="玩家名称不能为空",
            details=[{"field": "player_name", "message": "玩家名称不能为空"}],
        )

    server_name = str(data.get("server_name") or "").strip()
    if not server_name:
        return api_error(
            status_code=422,
            code="validation_error",
            message="服务器名称不能为空",
            details=[{"field": "server_name", "message": "服务器名称不能为空"}],
        )

    event = str(data.get("event") or "").strip().lower()
    if event not in _ALLOWED_EVENTS:
        return api_error(
            status_code=422,
            code="validation_error",
            message="事件类型仅支持 online 或 offline",
            details=[{"field": "event", "message": "事件类型仅支持 online 或 offline"}],
        )

    bot = _pick_onebot_bot()
    if bot is None:
        logger.warning(
            f"推送玩家上下线通知失败：player_name={player_name}，server_name={server_name}，event={event}，reason=机器人未连接"
        )
        return api_error(
            status_code=503,
            code="bot_unavailable",
            message="机器人未连接",
        )

    target_groups = _resolve_target_groups()
    if not target_groups:
        logger.warning(
            f"推送玩家上下线通知失败：player_name={player_name}，server_name={server_name}，event={event}，reason=未配置有效通知群"
        )
        return api_error(
            status_code=409,
            code="no_target_group",
            message="未配置有效的通知群",
        )

    bound_user_id = _resolve_user_id_by_name(player_name)
    display_name = f"{player_name}（{bound_user_id}）" if bound_user_id else player_name

    config = nonebot.get_driver().config
    if event == "online":
        template = str(
            getattr(config, "player_notify_online_template", "") or ""
        ).strip() or "[{server}]{player} 上线了"
    else:
        template = str(
            getattr(config, "player_notify_offline_template", "") or ""
        ).strip() or "[{server}]{player} 下线了"
    text = template.replace("{player}", display_name).replace("{server}", server_name)

    sent_groups: list[int] = []
    failed_groups: list[int] = []
    for gid in target_groups:
        try:
            await bot.call_api("send_group_msg", group_id=gid, message=text)
        except Exception as exc:
            failed_groups.append(gid)
            logger.warning(
                f"推送玩家上下线通知到群失败：group_id={gid}，player_name={player_name}，event={event}，reason={exc}"
            )
            continue
        sent_groups.append(gid)

    logger.info(
        f"推送玩家上下线通知完成：player_name={player_name}，server_name={server_name}，event={event}，"
        f"sent={sent_groups}，failed={failed_groups}"
    )

    return api_success(
        data={
            "sent_groups": sent_groups,
            "failed_groups": failed_groups,
        }
    )
