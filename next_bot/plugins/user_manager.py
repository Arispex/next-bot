import re

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg
from next_bot.command_config import command_control
from next_bot.message_parser import (
    parse_command_args_with_fallback,
    resolve_user_id_arg_with_fallback,
)
from next_bot.permissions import require_permission

from next_bot.db import Server, User, get_session
from next_bot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

add_matcher = on_command("注册账号")
sync_matcher = on_command("同步白名单")
info_matcher = on_command("用户信息")
self_info_matcher = on_command("我的信息")

ADD_USAGE = "格式错误，正确格式：注册账号 <用户名称>"
SYNC_USAGE = "格式错误，正确格式：同步白名单"
INFO_USAGE = "格式错误，正确格式：用户信息 <用户 ID/@用户/用户名称>"
SELF_INFO_USAGE = "格式错误，正确格式：我的信息"
MAX_USER_NAME_LENGTH = 16


def _validate_user_name(name: str) -> str | None:
    value = name.strip()
    if not value:
        return "用户名称不能为空"
    if len(value) > MAX_USER_NAME_LENGTH:
        return f"用户名称过长，最多 {MAX_USER_NAME_LENGTH} 个字符"
    if value.isdigit():
        return "用户名称不能为纯数字"
    if not re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fff]+", value):
        return "用户名称不能包含符号，只能使用中文、英文和数字"
    return None


async def _sync_whitelist_to_all_servers(
    user_id: str, name: str
) -> list[tuple[Server, bool, str]]:
    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    results: list[tuple[Server, bool, str]] = []
    for server in servers:
        try:
            response = await request_server_api(
                server,
                "/v3/server/rawcmd",
                params={"cmd": f"/bwl add {name}"},
            )
        except TShockRequestError:
            logger.info(
                f"白名单同步失败：server_id={server.id} user_id={user_id} name={name} reason=无法连接服务器"
            )
            results.append((server, False, "无法连接服务器"))
            continue

        if is_success(response):
            results.append((server, True, ""))
            continue

        reason = get_error_reason(response)
        logger.info(
            "白名单同步失败："
            f"server_id={server.id} user_id={user_id} name={name} "
            f"http_status={response.http_status} api_status={response.api_status} reason={reason}"
        )
        results.append((server, False, reason))
    return results


@add_matcher.handle()
@command_control(
    command_key="user.register",
    display_name="注册账号",
    permission="um.add",
    description="注册当前 QQ 对应的游戏账号",
)
@require_permission("um.add")
async def handle_add_whitelist(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "注册账号")
    if len(args) != 1:
        await bot.send(event, ADD_USAGE)
        return

    name = args[0].strip()
    invalid_reason = _validate_user_name(name)
    if invalid_reason is not None:
        await bot.send(event, f"注册失败，{invalid_reason}")
        return

    user_id = event.get_user_id()

    session = get_session()
    try:
        exists = session.query(User).filter(User.user_id == user_id).first()
        if exists is not None:
            logger.info(f"账号已注册：user_id={user_id} name={exists.name}")
            await bot.send(event, "注册失败，该账号已注册")
            return
        name_exists = session.query(User).filter(User.name == name).first()
        if name_exists is not None:
            logger.info(f"用户名称已存在：name={name}")
            await bot.send(event, "注册失败，用户名称已被占用")
            return

        user = User(user_id=user_id, name=name, group="default")
        session.add(user)
        session.commit()
    finally:
        session.close()

    await _sync_whitelist_to_all_servers(user_id, name)

    logger.info(f"注册账号成功：user_id={user_id} name={name}")
    await bot.send(event, "注册成功")


@sync_matcher.handle()
@command_control(
    command_key="user.sync_whitelist",
    display_name="同步白名单",
    permission="um.sync",
    description="将当前用户同步到所有服务器白名单",
)
@require_permission("um.sync")
async def handle_sync_whitelist(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "同步白名单")
    if args:
        await bot.send(event, SYNC_USAGE)
        return

    user_id = event.get_user_id()
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close()

    if user is None:
        await bot.send(event, "同步失败，未注册账号")
        return

    results = await _sync_whitelist_to_all_servers(user_id, user.name)
    if not results:
        await bot.send(event, "同步失败，暂无可同步的服务器")
        return

    lines: list[str] = []
    for server, success, reason in results:
        if success:
            lines.append(f"{server.id}.{server.name}：同步成功")
        else:
            lines.append(f"{server.id}.{server.name}：同步失败，{reason}")

    logger.info(
        f"同步白名单完成：user_id={user_id} name={user.name} server_count={len(results)}"
    )
    await bot.send(event, "\n".join(lines))


@info_matcher.handle()
@command_control(
    command_key="user.info",
    display_name="用户信息",
    permission="um.info",
    description="查询指定用户信息",
)
@require_permission("um.info")
async def handle_user_info(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "用户信息")
    if len(args) != 1:
        await bot.send(event, INFO_USAGE)
        return

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "用户信息",
    )
    if parse_error == "missing":
        await bot.send(event, INFO_USAGE)
        return
    if parse_error == "name_not_found":
        await bot.send(event, "查询失败，用户名称不存在")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, "查询失败，用户名称不唯一，请使用用户 ID 或 @用户")
        return
    if target_user_id is None:
        await bot.send(event, "查询失败，用户参数解析失败")
        return

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == target_user_id).first()
    finally:
        session.close()

    if user is None:
        await bot.send(event, "查询失败，用户不存在")
        return

    created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
    message = "\n".join(
        [
            f"用户 ID：{user.user_id}",
            f"用户名称：{user.name}",
            f"权限：{user.permissions or '无'}",
            f"身份组：{user.group}",
            f"创建时间：{created_at}",
        ]
    )
    await bot.send(event, message)


@self_info_matcher.handle()
@command_control(
    command_key="user.self_info",
    display_name="我的信息",
    permission="um.info.self",
    description="查询当前用户信息",
)
@require_permission("um.info.self")
async def handle_self_info(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "我的信息")
    if args:
        await bot.send(event, SELF_INFO_USAGE)
        return

    user_id = event.get_user_id()
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close()

    if user is None:
        await bot.send(event, "查询失败，未注册账号")
        return

    created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
    message = "\n".join(
        [
            f"用户 ID：{user.user_id}",
            f"用户名称：{user.name}",
            f"权限：{user.permissions or '无'}",
            f"身份组：{user.group}",
            f"创建时间：{created_at}",
        ]
    )
    await bot.send(event, message)
