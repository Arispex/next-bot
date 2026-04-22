from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nonebot.log import logger

from nextbot.access_control import get_owner_ids
from nextbot.db import Server, User, get_session
from nextbot.time_utils import db_now_utc_naive
from nextbot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

BanDBCode = Literal["not_found", "owner_protected", "already_banned", "banned"]


@dataclass
class BanDBResult:
    code: BanDBCode
    user_name: str = ""
    user_qq: str = ""
    previous_reason: str = ""


def apply_ban_to_db(user_id: str, reason: str) -> BanDBResult:
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return BanDBResult(code="not_found")
        if str(user.user_id) in get_owner_ids():
            return BanDBResult(
                code="owner_protected",
                user_name=user.name,
                user_qq=str(user.user_id),
            )
        if user.is_banned:
            return BanDBResult(
                code="already_banned",
                user_name=user.name,
                user_qq=str(user.user_id),
                previous_reason=user.ban_reason or "",
            )
        user.is_banned = True
        user.banned_at = db_now_utc_naive()
        user.ban_reason = reason
        session.commit()
        return BanDBResult(
            code="banned",
            user_name=user.name,
            user_qq=str(user.user_id),
        )
    finally:
        session.close()


async def sync_user_to_blacklist(user_name: str, reason: str) -> list[str]:
    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    lines: list[str] = []
    if not servers:
        lines.append("🖥️ 同步服务器黑名单结果：ℹ️ 暂无服务器")
        return lines

    lines.append("🖥️ 同步服务器黑名单结果：")
    for server in servers:
        try:
            check_response = await request_server_api(server, "/nextbot/blacklist")
        except TShockRequestError:
            lines.append(f"{server.id}.{server.name}：❌ 添加失败，无法连接服务器")
            continue

        if is_success(check_response):
            entries = check_response.payload.get("entries", [])
            already_exists = any(
                str(e.get("username", "")).lower() == user_name.lower()
                for e in entries
                if isinstance(e, dict)
            )
            if already_exists:
                lines.append(f"{server.id}.{server.name}：ℹ️ 已存在于黑名单中")
                continue

        try:
            response = await request_server_api(
                server,
                f"/nextbot/blacklist/add/{user_name}",
                params={"reason": reason},
            )
        except TShockRequestError:
            lines.append(f"{server.id}.{server.name}：❌ 添加失败，无法连接服务器")
            continue

        if is_success(response):
            lines.append(f"{server.id}.{server.name}：✅ 添加成功")
        else:
            lines.append(f"{server.id}.{server.name}：❌ 添加失败，{get_error_reason(response)}")

    logger.info(
        f"黑名单同步完成：user_name={user_name} server_count={len(servers)}"
    )
    return lines
