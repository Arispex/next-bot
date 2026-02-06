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

ONLINE_USAGE = "格式错误，正确格式：在线"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


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
