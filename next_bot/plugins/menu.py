from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.params import CommandArg
from next_bot.message_parser import parse_command_args_with_fallback
from next_bot.permissions import require_permission

menu_matcher = on_command("菜单")
basic_matcher = on_command("基础功能")
group_matcher = on_command("身份组管理")
permission_matcher = on_command("权限管理")
server_matcher = on_command("服务器管理")
user_matcher = on_command("用户管理")
agent_matcher = on_command("代理功能")

MENU_USAGE = "格式错误，正确格式：菜单"
BASIC_USAGE = "格式错误，正确格式：基础功能"
GROUP_USAGE = "格式错误，正确格式：身份组管理"
PERMISSION_USAGE = "格式错误，正确格式：权限管理"
SERVER_USAGE = "格式错误，正确格式：服务器管理"
USER_USAGE = "格式错误，正确格式：用户管理"
AGENT_USAGE = "格式错误，正确格式：代理功能"

MENU_TEXT = "\n".join(
    [
        "基础功能",
        "身份组管理",
        "权限管理",
        "服务器管理",
        "用户管理",
        "代理功能",
    ]
)

BASIC_TEXT = "\n".join(["在线", "执行", "自踢", "用户背包"])
GROUP_TEXT = "\n".join(
    [
        "身份组列表",
        "添加身份组",
        "删除身份组",
        "继承身份组",
        "取消继承身份组",
        "添加身份组权限",
        "删除身份组权限",
    ]
)
PERMISSION_TEXT = "\n".join(
    [
        "添加用户权限",
        "删除用户权限",
        "修改用户身份组",
    ]
)
SERVER_TEXT = "\n".join(
    [
        "添加服务器",
        "删除服务器",
        "服务器列表",
        "测试连通性",
    ]
)
USER_TEXT = "\n".join(["注册账号", "同步白名单"])
AGENT_TEXT = "\n".join(["代理", "允许执行命令", "拒绝执行命令"])
@menu_matcher.handle()
@require_permission("mn.menu")
async def handle_menu(bot: Bot, event: Event, arg: Message = CommandArg()):
    args = parse_command_args_with_fallback(event, arg, "菜单")
    if args:
        await bot.send(event, MENU_USAGE)
        return
    await bot.send(event, MENU_TEXT)


@basic_matcher.handle()
@require_permission("mn.basic")
async def handle_basic_menu(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "基础功能")
    if args:
        await bot.send(event, BASIC_USAGE)
        return
    await bot.send(event, BASIC_TEXT)


@group_matcher.handle()
@require_permission("mn.group")
async def handle_group_menu(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "身份组管理")
    if args:
        await bot.send(event, GROUP_USAGE)
        return
    await bot.send(event, GROUP_TEXT)


@permission_matcher.handle()
@require_permission("mn.permission")
async def handle_permission_menu(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "权限管理")
    if args:
        await bot.send(event, PERMISSION_USAGE)
        return
    await bot.send(event, PERMISSION_TEXT)


@server_matcher.handle()
@require_permission("mn.server")
async def handle_server_menu(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "服务器管理")
    if args:
        await bot.send(event, SERVER_USAGE)
        return
    await bot.send(event, SERVER_TEXT)


@user_matcher.handle()
@require_permission("mn.user")
async def handle_user_menu(bot: Bot, event: Event, arg: Message = CommandArg()):
    args = parse_command_args_with_fallback(event, arg, "用户管理")
    if args:
        await bot.send(event, USER_USAGE)
        return
    await bot.send(event, USER_TEXT)


@agent_matcher.handle()
@require_permission("mn.agent")
async def handle_agent_menu(bot: Bot, event: Event, arg: Message = CommandArg()):
    args = parse_command_args_with_fallback(event, arg, "代理功能")
    if args:
        await bot.send(event, AGENT_USAGE)
        return
    await bot.send(event, AGENT_TEXT)
