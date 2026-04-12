from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.command_config import command_control, raise_command_usage
from nextbot.db import Server, User, get_session
from nextbot.message_parser import parse_command_args_with_fallback, resolve_user_id_arg_with_fallback
from nextbot.permissions import require_permission
from nextbot.time_utils import db_now_utc_naive
from nextbot.tshock_api import TShockRequestError, get_error_reason, is_success, request_server_api

ban_matcher = on_command("封禁用户")
unban_matcher = on_command("解封用户")


@ban_matcher.handle()
@command_control(
    command_key="admin.ban",
    display_name="封禁用户",
    permission="admin.ban",
    description="封禁用户并将其加入所有服务器黑名单",
    usage="封禁用户 <用户名称/QQ/@用户> <原因>",
    admin=True,
)
@require_permission("admin.ban")
async def handle_ban(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event, arg, "封禁用户", arg_index=0,
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, at + " 封禁失败，未找到该用户")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, at + " 封禁失败，用户名存在重复，请使用 QQ 或 @用户")
        return
    if parse_error:
        raise_command_usage()

    args = parse_command_args_with_fallback(event, arg, "封禁用户")
    if len(args) < 2:
        raise_command_usage()
    reason = " ".join(args[1:]).strip()
    if not reason:
        raise_command_usage()

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == target_user_id).first()
        if user is None:
            await bot.send(event, at + " 封禁失败，未找到该用户")
            return

        if user.is_banned:
            await bot.send(event, at + f" 封禁失败，该用户已被封禁，原因：{user.ban_reason}")
            return

        user.is_banned = True
        user.banned_at = db_now_utc_naive()
        user.ban_reason = reason
        session.commit()

        user_name = user.name
        user_qq = user.user_id
    finally:
        session.close()

    logger.info(
        f"用户封禁成功：user_id={user_qq} name={user_name} reason={reason}"
    )

    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    lines: list[str] = [f"封禁成功，用户 {user_name}（{user_qq}）已被封禁，原因：{reason}"]

    if not servers:
        lines.append("同步服务器黑名单结果：暂无服务器")
    else:
        lines.append("同步服务器黑名单结果：")
        for server in servers:
            try:
                check_response = await request_server_api(
                    server,
                    "/nextbot/blacklist",
                )
            except TShockRequestError:
                lines.append(f"{server.id}.{server.name}：添加失败，无法连接服务器")
                continue

            if is_success(check_response):
                entries = check_response.payload.get("entries", [])
                already_exists = any(
                    str(e.get("username", "")).lower() == user_name.lower()
                    for e in entries
                    if isinstance(e, dict)
                )
                if already_exists:
                    lines.append(f"{server.id}.{server.name}：已存在于黑名单中")
                    continue

            try:
                response = await request_server_api(
                    server,
                    f"/nextbot/blacklist/add/{user_name}",
                    params={"reason": reason},
                )
            except TShockRequestError:
                lines.append(f"{server.id}.{server.name}：添加失败，无法连接服务器")
                continue

            if is_success(response):
                lines.append(f"{server.id}.{server.name}：添加成功")
            else:
                error_msg = get_error_reason(response)
                lines.append(f"{server.id}.{server.name}：添加失败，{error_msg}")

    logger.info(
        f"封禁用户黑名单同步完成：user_id={user_qq} name={user_name} server_count={len(servers)}"
    )
    await bot.send(event, at + "\n" + "\n".join(lines))


@unban_matcher.handle()
@command_control(
    command_key="admin.unban",
    display_name="解封用户",
    permission="admin.unban",
    description="解除封禁用户并将其从所有服务器黑名单移除",
    usage="解封用户 <用户名称/QQ/@用户>",
    admin=True,
)
@require_permission("admin.unban")
async def handle_unban(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event, arg, "解封用户", arg_index=0,
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, at + " 解封失败，未找到该用户")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, at + " 解封失败，用户名存在重复，请使用 QQ 或 @用户")
        return
    if parse_error:
        raise_command_usage()

    args = parse_command_args_with_fallback(event, arg, "解封用户")
    if len(args) != 1:
        raise_command_usage()

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == target_user_id).first()
        if user is None:
            await bot.send(event, at + " 解封失败，未找到该用户")
            return

        if not user.is_banned:
            await bot.send(event, at + " 解封失败，该用户未被封禁")
            return

        user.is_banned = False
        user.banned_at = None
        user.ban_reason = ""
        session.commit()

        user_name = user.name
        user_qq = user.user_id
    finally:
        session.close()

    logger.info(f"用户解封成功：user_id={user_qq} name={user_name}")

    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    lines: list[str] = [f"解封成功，用户 {user_name}（{user_qq}）已解除封禁"]

    if not servers:
        lines.append("同步服务器黑名单结果：暂无服务器")
    else:
        lines.append("同步服务器黑名单结果：")
        for server in servers:
            try:
                check_response = await request_server_api(
                    server,
                    "/nextbot/blacklist",
                )
            except TShockRequestError:
                lines.append(f"{server.id}.{server.name}：移除失败，无法连接服务器")
                continue

            if is_success(check_response):
                entries = check_response.payload.get("entries", [])
                exists = any(
                    str(e.get("username", "")).lower() == user_name.lower()
                    for e in entries
                    if isinstance(e, dict)
                )
                if not exists:
                    lines.append(f"{server.id}.{server.name}：不在黑名单中")
                    continue

            try:
                response = await request_server_api(
                    server,
                    f"/nextbot/blacklist/remove/{user_name}",
                )
            except TShockRequestError:
                lines.append(f"{server.id}.{server.name}：移除失败，无法连接服务器")
                continue

            if is_success(response):
                lines.append(f"{server.id}.{server.name}：移除成功")
            else:
                error_msg = get_error_reason(response)
                lines.append(f"{server.id}.{server.name}：移除失败，{error_msg}")

    logger.info(
        f"解封用户黑名单同步完成：user_id={user_qq} name={user_name} server_count={len(servers)}"
    )
    await bot.send(event, at + "\n" + "\n".join(lines))
