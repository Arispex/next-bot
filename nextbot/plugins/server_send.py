import re

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.command_config import command_control, raise_command_usage
from nextbot.db import Server, User, get_session
from nextbot.message_parser import parse_command_text_with_fallback
from nextbot.permissions import require_permission
from nextbot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)
from nextbot.text_utils import reply_failure, reply_success


send_matcher = on_command("发送")

_WHITESPACE_RE = re.compile(r"\s+")


def _parse_send_arg_text(text: str) -> tuple[int, str] | None:
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None
    server_id_text, content = parts
    try:
        server_id = int(server_id_text)
    except ValueError:
        return None
    normalized = _WHITESPACE_RE.sub(" ", content).strip()
    if not normalized:
        return None
    return server_id, normalized


@send_matcher.handle()
@command_control(
    command_key="server.send",
    display_name="发送",
    permission="server.send",
    description="在指定服务器的游戏内广播一条 QQ 消息",
    usage="发送 <服务器 ID> <内容>",
    category="服务器工具",
)
@require_permission("server.send")
async def handle_send(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))
    text = parse_command_text_with_fallback(event, arg, "发送")
    parsed = _parse_send_arg_text(text)
    if parsed is None:
        raise_command_usage()

    target_id, content = parsed
    user_id = event.get_user_id()

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        server = session.query(Server).filter(Server.id == target_id).first()
    finally:
        session.close()

    if user is None:
        await bot.send(event, at + " " + reply_failure("发送", "请先注册账号"))
        return
    if server is None:
        await bot.send(event, at + " " + reply_failure("发送", "服务器不存在"))
        return

    raw_cmd = f"/say {user.name}（{user_id}）：{content}"
    logger.info(
        f"QQ 消息转发到服务器：server_id={target_id}，user_id={user_id}，"
        f"name={user.name}，content_preview={content[:40]}"
    )

    try:
        response = await request_server_api(
            server,
            "/v3/server/rawcmd",
            params={"cmd": raw_cmd},
        )
    except TShockRequestError:
        await bot.send(event, at + " " + reply_failure("发送", "无法连接服务器"))
        return

    if not is_success(response):
        await bot.send(event, at + " " + reply_failure("发送", f"{get_error_reason(response)}"))
        return

    await bot.send(event, at + " " + reply_success("发送"))
