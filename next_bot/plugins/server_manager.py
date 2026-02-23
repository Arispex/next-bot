from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.command_config import command_control
from next_bot.db import Server, get_session
from next_bot.message_parser import parse_command_args_with_fallback
from next_bot.permissions import require_permission
from next_bot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

add_matcher = on_command("添加服务器")
delete_matcher = on_command("删除服务器")
list_matcher = on_command("服务器列表")
test_matcher = on_command("测试连通性")

ADD_USAGE = "格式错误，正确格式：添加服务器 <服务器名称> <IP> <游戏端口> <RestAPI 端口> <RestAPI Token>"
DELETE_USAGE = "格式错误，正确格式：删除服务器 <服务器 ID>"
LIST_USAGE = "格式错误，正确格式：服务器列表"
TEST_USAGE = "格式错误，正确格式：测试连通性 <服务器 ID>"
@add_matcher.handle()
@command_control(
    command_key="server.add",
    display_name="添加服务器",
    permission="server.add",
    description="新增服务器配置",
)
@require_permission("server.add")
async def handle_add_server(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "添加服务器")
    if len(args) != 5:
        await bot.send(event, ADD_USAGE)
        return

    name, ip, game_port, restapi_port, token = args
    session = get_session()
    try:
        count = session.query(Server).count()
        server = Server(
            id=count + 1,
            name=name,
            ip=ip,
            game_port=game_port,
            restapi_port=restapi_port,
            token=token,
        )
        session.add(server)
        session.commit()
    finally:
        session.close()

    logger.info(
        f"添加服务器成功：ID={count + 1} name={name} ip={ip} game_port={game_port} restapi_port={restapi_port}"
    )
    await bot.send(event, "添加成功")


@delete_matcher.handle()
@command_control(
    command_key="server.delete",
    display_name="删除服务器",
    permission="server.delete",
    description="删除服务器并重排 ID",
)
@require_permission("server.delete")
async def handle_delete_server(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "删除服务器")
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
            await bot.send(event, "删除失败，服务器不存在")
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
@command_control(
    command_key="server.list",
    display_name="服务器列表",
    permission="server.list",
    description="输出服务器列表",
)
@require_permission("server.list")
async def handle_list_servers(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "服务器列表")
    if args:
        await bot.send(event, LIST_USAGE)
        return

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
        lines.append(f"端口：{server.game_port}")
        lines.append("")

    message = "\n".join(lines).rstrip()
    logger.info(f"输出服务器列表，共 {len(servers)} 条")
    await bot.send(event, message)


@test_matcher.handle()
@command_control(
    command_key="server.test",
    display_name="测试连通性",
    permission="server.test",
    description="测试服务器 RestAPI 连通性",
)
@require_permission("server.test")
async def handle_test_server(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "测试连通性")
    if len(args) != 1:
        await bot.send(event, TEST_USAGE)
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await bot.send(event, TEST_USAGE)
        return

    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == target_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "测试失败，服务器不存在")
        return

    try:
        response = await request_server_api(server, "/tokentest")
    except TShockRequestError:
        logger.info(
            f"测试连通性失败：id={target_id} ip={server.ip} port={server.restapi_port}"
        )
        await bot.send(event, "测试失败，无法连接服务器")
        return

    status_code = response.http_status
    status_value = response.api_status
    logger.info(
        f"测试连通性完成：id={target_id} http={status_code} status={status_value}"
    )

    if is_success(response):
        await bot.send(event, "测试成功，一切正常")
        return

    reason = get_error_reason(response)
    await bot.send(event, f"测试失败，{reason}")
