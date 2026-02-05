from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.console import Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Server, get_session

add_matcher = on_command("添加服务器")
delete_matcher = on_command("删除服务器")
list_matcher = on_command("服务器列表")

ADD_USAGE = "格式错误，正确格式：添加服务器 [name] [IP] [port] [key]"
DELETE_USAGE = "格式错误，正确格式：删除服务器 [ID]"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


@add_matcher.handle()
async def handle_add_server(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if len(args) != 4:
        await bot.send(event, ADD_USAGE)
        return

    name, ip, port, key = args
    session = get_session()
    try:
        count = session.query(Server).count()
        server = Server(id=count + 1, name=name, ip=ip, port=port, key=key)
        session.add(server)
        session.commit()
    finally:
        session.close()

    logger.info(
        f"添加服务器成功：ID={count + 1} name={name} ip={ip} port={port}"
    )
    await bot.send(event, "添加成功")


@delete_matcher.handle()
async def handle_delete_server(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if len(args) != 1:
        await bot.send(event, DELETE_USAGE)
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await bot.send(event, DELETE_USAGE)
        return

    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == target_id).first()
        if server is None:
            await bot.send(event, "未找到匹配的服务器记录")
            return

        deleted_id = server.id
        session.delete(server)
        session.flush()

        session.query(Server).filter(Server.id > deleted_id).update(
            {Server.id: Server.id - 1}, synchronize_session=False
        )
        session.commit()
    finally:
        session.close()

    logger.info(f"删除服务器成功：ID={deleted_id}")
    await bot.send(event, "删除成功")


@list_matcher.handle()
async def handle_list_servers(bot: Bot, event: MessageEvent):
    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    if not servers:
        await bot.send(event, "暂无服务器")
        return

    lines: list[str] = []
    for server in servers:
        lines.append(f"{server.id}.{server.name}")
        lines.append(f"IP：{server.ip}")
        lines.append(f"端口：{server.port}")
        lines.append("")

    message = "\n".join(lines).rstrip()
    logger.info(f"输出服务器列表，共 {len(servers)} 条")
    await bot.send(event, message)
