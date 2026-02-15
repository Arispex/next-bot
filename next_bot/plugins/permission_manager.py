from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Group, User, get_session
from next_bot.message_parser import (
    parse_command_args_with_fallback,
    resolve_user_id_arg_with_fallback,
)
from next_bot.permissions import (
    add_permission,
    remove_permission,
    require_permission,
)

add_user_perm_matcher = on_command("添加用户权限")
remove_user_perm_matcher = on_command("删除用户权限")
set_user_group_matcher = on_command("修改用户身份组")

ADD_USER_PERM_USAGE = "格式错误，正确格式：添加用户权限 <用户 ID/@用户/用户名称> <权限名称>"
REMOVE_USER_PERM_USAGE = "格式错误，正确格式：删除用户权限 <用户 ID/@用户/用户名称> <权限名称>"
SET_USER_GROUP_USAGE = "格式错误，正确格式：修改用户身份组 <用户 ID/@用户/用户名称> <身份组名称>"
@add_user_perm_matcher.handle()
@require_permission("pm.user.add_perm")
async def handle_add_user_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "添加用户权限")
    if len(args) != 2:
        await bot.send(event, ADD_USER_PERM_USAGE)
        return

    user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "添加用户权限",
    )
    if parse_error == "missing":
        await bot.send(event, ADD_USER_PERM_USAGE)
        return
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
@require_permission("pm.user.remove_perm")
async def handle_remove_user_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "删除用户权限")
    if len(args) != 2:
        await bot.send(event, REMOVE_USER_PERM_USAGE)
        return

    user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "删除用户权限",
    )
    if parse_error == "missing":
        await bot.send(event, REMOVE_USER_PERM_USAGE)
        return
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
@require_permission("pm.user.group")
async def handle_set_user_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "修改用户身份组")
    if len(args) != 2:
        await bot.send(event, SET_USER_GROUP_USAGE)
        return

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "修改用户身份组",
    )
    if parse_error == "missing":
        await bot.send(event, SET_USER_GROUP_USAGE)
        return
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
