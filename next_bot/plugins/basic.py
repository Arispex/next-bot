from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Server, get_session
from next_bot.permissions import require_permission
from next_bot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

online_matcher = on_command("在线")
execute_matcher = on_command("执行")

ONLINE_USAGE = "格式错误，正确格式：在线"
EXECUTE_USAGE = "格式错误，正确格式：执行 <服务器 ID> <命令>"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


def _parse_execute_arg(arg: Message) -> tuple[int, str] | None:
    text = arg.extract_plain_text().strip()
    if not text:
        return None

    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None

    server_id_text, command = parts
    try:
        server_id = int(server_id_text)
    except ValueError:
        return None

    command_text = command.strip()
    if not command_text:
        return None
    return server_id, command_text


def _extract_response_text(payload: dict[str, object]) -> str:
    value = payload.get("response")
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(lines)
    if isinstance(value, str):
        return value.strip()
    return ""


@online_matcher.handle()
@require_permission("bf.online")
async def handle_online(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if args:
        await bot.send(event, ONLINE_USAGE)
        return

    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    if not servers:
        await bot.send(event, "查询失败，暂无服务器")
        return

    lines: list[str] = []
    for server in servers:
        lines.append(f"{server.id}.{server.name}")
        try:
            response = await request_server_api(
                server,
                "/v2/server/status",
                params={"players": "true"},
            )
        except TShockRequestError:
            lines.append("查询失败，无法连接服务器")
            continue

        if not is_success(response):
            lines.append(f"查询失败，{get_error_reason(response)}")
            continue

        players = response.payload.get("players")
        if not isinstance(players, list):
            lines.append("查询失败，返回数据格式错误")
            continue

        playercount = response.payload.get("playercount")
        maxplayers = response.payload.get("maxplayers")
        if not isinstance(playercount, int) or not isinstance(maxplayers, int):
            lines.append("查询失败，返回数据格式错误")
            continue

        if not players:
            lines.append("无玩家在线")
            continue

        lines.append(f"在线玩家({playercount}/{maxplayers})")
        nicknames: list[str] = []
        for player in players:
            if isinstance(player, dict):
                nickname = str(player.get("nickname", "")).strip()
                if nickname:
                    nicknames.append(nickname)
                    continue
            nicknames.append(str(player))

        player_names = ",".join(nicknames)
        lines.append(player_names)

    logger.info(f"在线查询完成：server_count={len(servers)}")
    await bot.send(event, "\n".join(lines))


@execute_matcher.handle()
@require_permission("bf.exec")
async def handle_execute(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    parsed = _parse_execute_arg(arg)
    if parsed is None:
        await bot.send(event, EXECUTE_USAGE)
        return

    target_id, command = parsed
    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == target_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "执行失败，服务器不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v3/server/rawcmd",
            params={"cmd": command},
        )
    except TShockRequestError:
        await bot.send(event, "执行失败，无法连接服务器")
        return

    if not is_success(response):
        await bot.send(event, f"执行失败，{get_error_reason(response)}")
        return

    result_text = _extract_response_text(response.payload)
    if result_text:
        await bot.send(event, f"执行成功，返回内容：\n{result_text}")
        return

    await bot.send(event, "执行成功，无返回内容")
