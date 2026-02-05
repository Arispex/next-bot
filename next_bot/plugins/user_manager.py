from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.console import Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.log import logger
from nonebot.params import CommandArg
from next_bot.permissions import require_permission

from next_bot.db import User, get_session

add_matcher = on_command("添加白名单")

ADD_USAGE = "格式错误，正确格式：添加白名单 [游戏名称]"


def _parse_args(arg: Message) -> list[str]:
    return [item for item in arg.extract_plain_text().strip().split() if item]


@add_matcher.handle()
@require_permission("um.add")
async def handle_add_whitelist(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    args = _parse_args(arg)
    if len(args) != 1:
        await bot.send(event, ADD_USAGE)
        return

    name = args[0]
    user_id = event.get_user_id()

    session = get_session()
    try:
        exists = session.query(User).filter(User.user_id == user_id).first()
        if exists is not None:
            logger.info(f"白名单已存在：user_id={user_id} name={exists.name}")
            await bot.send(event, "添加失败，该账号已在白名单")
            return
        name_exists = session.query(User).filter(User.name == name).first()
        if name_exists is not None:
            logger.info(f"白名单名称已存在：name={name}")
            await bot.send(event, "添加失败，名称已被占用")
            return

        user = User(user_id=user_id, name=name, group="default")
        session.add(user)
        session.commit()
    finally:
        session.close()

    logger.info(f"添加白名单成功：user_id={user_id} name={name}")
    await bot.send(event, "添加成功")
