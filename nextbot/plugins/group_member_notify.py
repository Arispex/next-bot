from __future__ import annotations

from typing import Any

import nonebot
from nonebot import on_notice
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import (
    Bot as OBV11Bot,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    Message as OBV11Message,
    MessageSegment as OBV11MessageSegment,
)
from nonebot.log import logger

from nextbot.access_control import get_group_ids

increase_matcher = on_notice()
decrease_matcher = on_notice()


def _group_allowed(group_id: int) -> bool:
    allowed = {g.strip() for g in get_group_ids() if g.strip().isdigit()}
    return str(group_id) in allowed


def _unescape(value: str) -> str:
    return value.replace("\\\\", "\x00").replace("\\n", "\n").replace("\x00", "\\")


def _load_template(field: str) -> str:
    config = nonebot.get_driver().config
    raw = str(getattr(config, field, "") or "")
    return _unescape(raw).strip()


async def _fetch_nickname(bot: OBV11Bot, user_id: int) -> str:
    try:
        info: Any = await bot.call_api("get_stranger_info", user_id=user_id, no_cache=True)
    except Exception as exc:
        logger.warning(f"拉取 QQ 昵称失败：user_id={user_id}，reason={exc}")
        return ""
    if isinstance(info, dict):
        return str(info.get("nickname") or "").strip()
    return ""


def _render(template: str, *, user_id: int, nickname: str) -> OBV11Message:
    display_nick = nickname or str(user_id)
    text = template.replace("{nickname}", display_nick).replace("{user_id}", str(user_id))
    parts = text.split("{at}")
    message = OBV11Message()
    for i, chunk in enumerate(parts):
        if chunk:
            message += OBV11MessageSegment.text(chunk)
        if i < len(parts) - 1:
            message += OBV11MessageSegment.at(user_id)
    return message


async def _send_group_notify(
    bot: Bot,
    group_id: int,
    user_id: int,
    template: str,
    *,
    event_label: str,
) -> None:
    if not isinstance(bot, OBV11Bot):
        return
    if not _group_allowed(group_id):
        return
    if not template:
        return

    nickname = await _fetch_nickname(bot, user_id)
    message = _render(template, user_id=user_id, nickname=nickname)
    if not message:
        return

    try:
        await bot.call_api("send_group_msg", group_id=group_id, message=message)
    except Exception as exc:
        logger.warning(
            f"发送{event_label}消息失败：group_id={group_id}，user_id={user_id}，reason={exc}"
        )
        return
    logger.info(
        f"发送{event_label}消息成功：group_id={group_id}，user_id={user_id}，nickname={nickname}"
    )


@increase_matcher.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
    config = nonebot.get_driver().config
    if not bool(getattr(config, "group_welcome_enabled", False)):
        return
    template = _load_template("group_welcome_template")
    await _send_group_notify(
        bot,
        group_id=event.group_id,
        user_id=event.user_id,
        template=template,
        event_label="入群欢迎",
    )


@decrease_matcher.handle()
async def handle_group_decrease(bot: Bot, event: GroupDecreaseNoticeEvent) -> None:
    config = nonebot.get_driver().config
    if not bool(getattr(config, "group_farewell_enabled", False)):
        return
    template = _load_template("group_farewell_template")
    await _send_group_notify(
        bot,
        group_id=event.group_id,
        user_id=event.user_id,
        template=template,
        event_label="退群送别",
    )
