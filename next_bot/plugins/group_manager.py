from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.command_config import command_control
from next_bot.db import Group, User, get_session
from next_bot.message_parser import parse_command_args_with_fallback
from next_bot.permissions import (
    add_inherit,
    add_permission,
    remove_inherit,
    remove_permission,
    require_permission,
)

list_matcher = on_command("身份组列表")
add_matcher = on_command("添加身份组")
delete_matcher = on_command("删除身份组")
inherit_matcher = on_command("继承身份组")
clear_inherit_matcher = on_command("取消继承身份组")
add_perm_matcher = on_command("添加身份组权限")
remove_perm_matcher = on_command("删除身份组权限")

ADD_USAGE = "格式错误，正确格式：添加身份组 <身份组名称>"
DELETE_USAGE = "格式错误，正确格式：删除身份组 <身份组名称>"
INHERIT_USAGE = "格式错误，正确格式：继承身份组 <身份组名称> <要继承的身份组名称>"
CLEAR_INHERIT_USAGE = "格式错误，正确格式：取消继承身份组 <身份组名称>"
ADD_PERM_USAGE = "格式错误，正确格式：添加身份组权限 <身份组名称> <权限名称>"
REMOVE_PERM_USAGE = "格式错误，正确格式：删除身份组权限 <身份组名称> <权限名称>"
LIST_USAGE = "格式错误，正确格式：身份组列表"
@list_matcher.handle()
@command_control(
    command_key="group.list",
    display_name="身份组列表",
    permission="group.list",
    description="显示所有身份组",
)
@require_permission("group.list")
async def handle_list_groups(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "身份组列表")
    if args:
        await bot.send(event, LIST_USAGE)
        return

    session = get_session()
    try:
        groups = session.query(Group).order_by(Group.name.asc()).all()
    finally:
        session.close()

    if not groups:
        await bot.send(event, "暂无身份组")
        return

    lines: list[str] = []
    for group in groups:
        lines.append(group.name)
        lines.append(f"权限：{group.permissions or '无'}")
        lines.append(f"继承：{group.inherits or '无'}")
        lines.append("")

    message = "\n".join(lines).rstrip()
    logger.info(f"输出身份组列表，共 {len(groups)} 条")
    await bot.send(event, message)


@add_matcher.handle()
@command_control(
    command_key="group.add",
    display_name="添加身份组",
    permission="group.add",
    description="新增身份组",
)
@require_permission("group.add")
async def handle_add_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "添加身份组")
    if len(args) != 1:
        await bot.send(event, ADD_USAGE)
        return

    name = args[0]
    session = get_session()
    try:
        exists = session.query(Group).filter(Group.name == name).first()
        if exists is not None:
            await bot.send(event, "添加失败，身份组已存在")
            return

        session.add(Group(name=name, permissions="", inherits=""))
        session.commit()
    finally:
        session.close()

    logger.info(f"添加身份组成功：name={name}")
    await bot.send(event, "添加成功")


@delete_matcher.handle()
@command_control(
    command_key="group.delete",
    display_name="删除身份组",
    permission="group.delete",
    description="删除身份组",
)
@require_permission("group.delete")
async def handle_delete_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "删除身份组")
    if len(args) != 1:
        await bot.send(event, DELETE_USAGE)
        return

    name = args[0]
    if name in {"guest", "default"}:
        await bot.send(event, "删除失败，系统内置身份组不可删除")
        return

    session = get_session()
    try:
        group = session.query(Group).filter(Group.name == name).first()
        if group is None:
            await bot.send(event, "删除失败，身份组不存在")
            return

        session.delete(group)
        session.flush()

        session.query(User).filter(User.group == name).update(
            {User.group: "guest"}, synchronize_session=False
        )
        all_groups = session.query(Group).all()
        for g in all_groups:
            parents = {p.strip() for p in g.inherits.split(",") if p.strip()}
            if name in parents:
                g.inherits = remove_inherit(g.inherits, name)
        session.commit()
    finally:
        session.close()

    logger.info(f"删除身份组成功：name={name}")
    await bot.send(event, "删除成功")


@inherit_matcher.handle()
@command_control(
    command_key="group.inherit.add",
    display_name="继承身份组",
    permission="group.inherit.add",
    description="设置身份组继承关系",
)
@require_permission("group.inherit.add")
async def handle_inherit_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "继承身份组")
    if len(args) != 2:
        await bot.send(event, INHERIT_USAGE)
        return

    child, parent = args
    if child == parent:
        await bot.send(event, "修改失败，不能继承到自身")
        return

    session = get_session()
    try:
        child_group = session.query(Group).filter(Group.name == child).first()
        parent_group = session.query(Group).filter(Group.name == parent).first()
        if child_group is None or parent_group is None:
            await bot.send(event, "修改失败，身份组不存在")
            return

        child_group.inherits = add_inherit(child_group.inherits, parent)
        session.commit()
    finally:
        session.close()

    logger.info(f"身份组继承成功：{child} -> {parent}")
    await bot.send(event, "修改成功")


@clear_inherit_matcher.handle()
@command_control(
    command_key="group.inherit.clear",
    display_name="取消继承身份组",
    permission="group.inherit.clear",
    description="清空身份组继承关系",
)
@require_permission("group.inherit.clear")
async def handle_clear_inherit_group(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "取消继承身份组")
    if len(args) != 1:
        await bot.send(event, CLEAR_INHERIT_USAGE)
        return

    name = args[0]
    session = get_session()
    try:
        group = session.query(Group).filter(Group.name == name).first()
        if group is None:
            await bot.send(event, "修改失败，身份组不存在")
            return

        group.inherits = ""
        session.commit()
    finally:
        session.close()

    logger.info(f"取消身份组继承成功：name={name}")
    await bot.send(event, "修改成功")


@add_perm_matcher.handle()
@command_control(
    command_key="group.permission.add",
    display_name="添加身份组权限",
    permission="group.permission.add",
    description="为身份组添加权限",
)
@require_permission("group.permission.add")
async def handle_add_group_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "添加身份组权限")
    if len(args) != 2:
        await bot.send(event, ADD_PERM_USAGE)
        return

    name, permission = args
    session = get_session()
    try:
        group = session.query(Group).filter(Group.name == name).first()
        if group is None:
            await bot.send(event, "添加失败，身份组不存在")
            return

        group.permissions = add_permission(group.permissions, permission)
        session.commit()
    finally:
        session.close()

    logger.info(f"添加身份组权限成功：name={name} permission={permission}")
    await bot.send(event, "添加成功")


@remove_perm_matcher.handle()
@command_control(
    command_key="group.permission.remove",
    display_name="删除身份组权限",
    permission="group.permission.remove",
    description="从身份组移除权限",
)
@require_permission("group.permission.remove")
async def handle_remove_group_perm(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "删除身份组权限")
    if len(args) != 2:
        await bot.send(event, REMOVE_PERM_USAGE)
        return

    name, permission = args
    session = get_session()
    try:
        group = session.query(Group).filter(Group.name == name).first()
        if group is None:
            await bot.send(event, "删除失败，身份组不存在")
            return

        group.permissions = remove_permission(group.permissions, permission)
        session.commit()
    finally:
        session.close()

    logger.info(f"删除身份组权限成功：name={name} permission={permission}")
    await bot.send(event, "删除成功")
