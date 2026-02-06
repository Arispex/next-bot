from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.console import Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Server, get_session
from next_bot.permissions import require_permission
from next_bot.tshock_api import TShockRequestError, request_server_api

online_matcher = on_command("在线")

ONLINE_USAGE = "格式错误，正确格式：在线"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


def _build_fail_reason(http_status: int, api_status: str) -> str:
    if http_status != 200:
        return f"HTTP 状态码 {http_status}"
    if api_status and api_status != "200":
        return f"接口状态 {api_status}"
    return "返回数据格式错误"


@online_matcher.handle()
@require_permission("bf.online")
async def handle_online(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
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

        if response.http_status != 200 or (
            response.api_status and response.api_status != "200"
        ):
            lines.append(
                f"查询失败，{_build_fail_reason(response.http_status, response.api_status)}"
            )
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
