import base64
from pathlib import Path

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.access_control import get_owner_ids
from nextbot.command_config import command_control, raise_command_usage
from nextbot.db import Group, User, get_session
from nextbot.message_parser import (
    parse_command_args_with_fallback,
    resolve_user_id_arg_with_fallback,
)
from nextbot.permissions import (
    add_permission,
    remove_permission,
    require_permission,
)
from nextbot.render_utils import resolve_render_theme
from nextbot.time_utils import beijing_filename_timestamp
from server.screenshot import RenderScreenshotError, ScreenshotOptions, screenshot_url
from server.web_server import create_admin_list_page

add_user_perm_matcher = on_command("添加用户权限")
remove_user_perm_matcher = on_command("删除用户权限")
set_user_group_matcher = on_command("修改用户身份组")
admin_list_matcher = on_command("管理员列表")

ADMIN_LIST_SCREENSHOT_OPTIONS = ScreenshotOptions(
    viewport_width=820,
    viewport_height=400,
    full_page=True,
)


async def _fetch_nickname_via_bot(bot: Bot, qq: str) -> str:
    """通过 OneBot V11 get_stranger_info 获取昵称，编码由 NapCat 处理。"""
    try:
        info = await bot.call_api("get_stranger_info", user_id=int(qq))
        return str(info.get("nickname", "")).strip()
    except Exception as exc:
        logger.info(f"get_stranger_info 失败：qq={qq} reason={exc}")
        return ""
@add_user_perm_matcher.handle()
@command_control(
    command_key="permission.user.add",
    admin=True,
    display_name="添加用户权限",
    permission="permission.user.add",
    description="为用户增加单独权限",
    usage="添加用户权限 <用户 ID/@用户/用户名称> <权限名称>",
)
@require_permission("permission.user.add")
async def handle_add_user_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "添加用户权限")
    if len(args) != 2:
        raise_command_usage()

    user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "添加用户权限",
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, "添加失败，用户名称不存在")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, "添加失败，用户名称不唯一，请使用用户 ID 或 @用户")
        return
    if user_id is None:
        await bot.send(event, "添加失败，用户参数解析失败")
        return

    permission = args[1]
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            await bot.send(event, "添加失败，用户不存在")
            return

        user.permissions = add_permission(user.permissions, permission)
        session.commit()
    finally:
        session.close()

    logger.info(f"添加用户权限成功：user_id={user_id} permission={permission}")
    await bot.send(event, "添加成功")


@remove_user_perm_matcher.handle()
@command_control(
    command_key="permission.user.remove",
    admin=True,
    display_name="删除用户权限",
    permission="permission.user.remove",
    description="从用户移除单独权限",
    usage="删除用户权限 <用户 ID/@用户/用户名称> <权限名称>",
)
@require_permission("permission.user.remove")
async def handle_remove_user_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "删除用户权限")
    if len(args) != 2:
        raise_command_usage()

    user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "删除用户权限",
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, "删除失败，用户名称不存在")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, "删除失败，用户名称不唯一，请使用用户 ID 或 @用户")
        return
    if user_id is None:
        await bot.send(event, "删除失败，用户参数解析失败")
        return

    permission = args[1]
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            await bot.send(event, "删除失败，用户不存在")
            return

        user.permissions = remove_permission(user.permissions, permission)
        session.commit()
    finally:
        session.close()

    logger.info(f"删除用户权限成功：user_id={user_id} permission={permission}")
    await bot.send(event, "删除成功")


@set_user_group_matcher.handle()
@command_control(
    command_key="permission.user.group.set",
    admin=True,
    display_name="修改用户身份组",
    permission="permission.user.group.set",
    description="调整用户所属身份组",
    usage="修改用户身份组 <用户 ID/@用户/用户名称> <身份组名称>",
)
@require_permission("permission.user.group.set")
async def handle_set_user_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "修改用户身份组")
    if len(args) != 2:
        raise_command_usage()

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "修改用户身份组",
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, "修改失败，用户名称不存在")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, "修改失败，用户名称不唯一，请使用用户 ID 或 @用户")
        return
    if target_user_id is None:
        await bot.send(event, "修改失败，用户参数解析失败")
        return

    group_name = args[1]
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == target_user_id).first()
        if user is None:
            await bot.send(event, "修改失败，用户不存在")
            return

        group = session.query(Group).filter(Group.name == group_name).first()
        if group is None:
            await bot.send(event, "修改失败，身份组不存在")
            return

        user.group = group_name
        session.commit()
    finally:
        session.close()

    logger.info(
        f"修改用户身份组成功：user_id={target_user_id} group={group_name}"
    )
    await bot.send(event, "修改成功")


@admin_list_matcher.handle()
@command_control(
    command_key="admin.list",
    display_name="管理员列表",
    admin=True,
    permission="admin.list",
    description="查看 Bot 管理员列表",
    usage="管理员列表",
)
@require_permission("admin.list")
async def handle_admin_list(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    args = parse_command_args_with_fallback(event, arg, "管理员列表")
    if args:
        raise_command_usage()

    owner_ids = sorted(get_owner_ids())
    if not owner_ids:
        await bot.send(event, "查询失败，未配置管理员（owner_id）")
        return

    logger.info(f"管理员列表查询：owner_count={len(owner_ids)}")

    admins: list[dict[str, str]] = []
    for qq in owner_ids:
        nickname = await _fetch_nickname_via_bot(bot, qq)
        admins.append({"user_id": qq, "nickname": nickname})
        logger.info(f"管理员昵称获取：qq={qq} nickname={nickname!r}")

    page_url = create_admin_list_page(admins=admins, theme=resolve_render_theme())
    logger.info(f"管理员列表渲染地址：admin_count={len(admins)} internal_url={page_url}")

    screenshot_path = Path("/tmp") / f"admin-list-{beijing_filename_timestamp()}.png"
    try:
        await screenshot_url(page_url, screenshot_path, options=ADMIN_LIST_SCREENSHOT_OPTIONS)
    except RenderScreenshotError as exc:
        await bot.send(event, f"查询失败，{exc}")
        return

    logger.info(f"管理员列表截图成功：file={screenshot_path}")
    if bot.adapter.get_name() == "OneBot V11":
        try:
            raw = screenshot_path.read_bytes()
            image_uri = f"base64://{base64.b64encode(raw).decode('ascii')}"
        except OSError:
            await bot.send(event, "查询失败，读取截图文件失败")
            return
        await bot.send(event, OBV11MessageSegment.image(file=image_uri))
        return
    await bot.send(event, f"截图成功，文件：{screenshot_path}")
