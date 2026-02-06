from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.console import Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.log import logger
from nonebot.params import CommandArg
from next_bot.permissions import require_permission

from next_bot.db import Server, User, get_session
from next_bot.tshock_api import TShockRequestError, request_server_api

add_matcher = on_command("添加白名单")
sync_matcher = on_command("同步白名单")

ADD_USAGE = "格式错误，正确格式：添加白名单 [游戏名称]"
SYNC_USAGE = "格式错误，正确格式：同步白名单"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


def _extract_fail_reason(
    response_payload: dict[str, object], http_status: int, api_status: str
) -> str:
    if http_status != 200:
        return f"HTTP 状态码 {http_status}"
    if api_status and api_status != "200":
        return f"接口状态 {api_status}"
    response_value = response_payload.get("response")
    if isinstance(response_value, list) and response_value:
        return str(response_value[0])
    if isinstance(response_value, str) and response_value.strip():
        return response_value.strip()
    return "未知错误"


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

        if response.http_status == 200 and (
            not response.api_status or response.api_status == "200"
        ):
            results.append((server, True, ""))
            continue

        reason = _extract_fail_reason(
            response.payload, response.http_status, response.api_status
        )
        logger.info(
            "白名单同步失败："
            f"server_id={server.id} user_id={user_id} name={name} "
            f"http_status={response.http_status} api_status={response.api_status} reason={reason}"
        )
        results.append((server, False, reason))
    return results


@add_matcher.handle()
@require_permission("um.add")
async def handle_add_whitelist(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if len(args) != 1:
        await bot.send(event, ADD_USAGE)
        return

    name = args[0]
    user_id = event.get_user_id()

    session = get_session()
    try:
        exists = session.query(User).filter(User.user_id == user_id).first()
        if exists is not None:
            logger.info(f"白名单已存在：user_id={user_id} name={exists.name}")
            await bot.send(event, "添加失败，该账号已在白名单")
            return
        name_exists = session.query(User).filter(User.name == name).first()
        if name_exists is not None:
            logger.info(f"白名单名称已存在：name={name}")
            await bot.send(event, "添加失败，名称已被占用")
            return

        user = User(user_id=user_id, name=name, group="default")
        session.add(user)
        session.commit()
    finally:
        session.close()

    await _sync_whitelist_to_all_servers(user_id, name)

    logger.info(f"添加白名单成功：user_id={user_id} name={name}")
    await bot.send(event, "添加成功")


@sync_matcher.handle()
@require_permission("um.sync")
async def handle_sync_whitelist(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    args = _parse_args(arg)
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
        await bot.send(event, "同步失败，用户未在白名单")
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
