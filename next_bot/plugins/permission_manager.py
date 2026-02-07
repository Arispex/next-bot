from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Group, User, get_session
from next_bot.permissions import (
    add_permission,
    remove_permission,
    require_permission,
)

add_user_perm_matcher = on_command("添加用户权限")
remove_user_perm_matcher = on_command("删除用户权限")
set_user_group_matcher = on_command("修改用户身份组")

ADD_USER_PERM_USAGE = "格式错误，正确格式：添加用户权限 <用户 ID> <权限名称>"
REMOVE_USER_PERM_USAGE = "格式错误，正确格式：删除用户权限 <用户 ID> <权限名称>"
SET_USER_GROUP_USAGE = "格式错误，正确格式：修改用户身份组 <用户 ID> <身份组>"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


@add_user_perm_matcher.handle()
@require_permission("pm.user.add_perm")
async def handle_add_user_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if len(args) != 2:
        await bot.send(event, ADD_USER_PERM_USAGE)
        return

    user_id, permission = args
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
    args = _parse_args(arg)
    if len(args) != 2:
        await bot.send(event, REMOVE_USER_PERM_USAGE)
        return

    user_id, permission = args
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
    args = _parse_args(arg)
    if len(args) != 2:
        await bot.send(event, SET_USER_GROUP_USAGE)
        return

    target_user_id, group_name = args
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
