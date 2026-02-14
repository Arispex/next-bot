import nonebot
from nonebot.adapters.console import Adapter as ConsoleAdapter
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters import Event
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.message import event_preprocessor

from server.web_server import start_render_server
from next_bot.access_control import get_group_ids, get_owner_ids
from next_bot.db import DB_PATH, init_db, ensure_default_groups, get_engine, Base

nonebot.init()

driver = nonebot.get_driver()
# driver.register_adapter(ConsoleAdapter)
driver.register_adapter(OneBotV11Adapter)


@event_preprocessor
async def _filter_allowed_messages(event: Event) -> None:
    if event.get_type() != "message":
        return

    owner_ids = get_owner_ids()
    group_ids = get_group_ids()
    message_type = getattr(event, "message_type", "")
    if message_type == "private":
        user_id = event.get_user_id()
        if user_id in owner_ids:
            return
        logger.info(f"消息被过滤：type=private user_id={user_id}")
        raise IgnoredException("private message blocked by owner_id allowlist")

    if message_type == "group":
        group_id = str(getattr(event, "group_id", "")).strip()
        user_id = event.get_user_id()
        if group_id in group_ids:
            return
        logger.info(
            f"消息被过滤：type=group group_id={group_id} user_id={user_id}"
        )
        raise IgnoredException("group message blocked by group_id allowlist")

    if event.get_user_id() == "user":
        return

    user_id = event.get_user_id()
    group_id = str(getattr(event, "group_id", "")).strip()
    logger.info(
        f"消息被过滤：type={message_type or 'unknown'} group_id={group_id} user_id={user_id}"
    )
    raise IgnoredException("message blocked by access allowlist")


@driver.on_startup
async def _init_database() -> None:
    start_render_server()
    if not DB_PATH.exists():
        logger.info("app.db 不存在，开始初始化数据库")
        init_db()
        logger.info("数据库初始化完成")
    else:
        logger.info("检测到 app.db，检查表结构")
        Base.metadata.create_all(get_engine())
        ensure_default_groups()
        logger.info("表结构检查完成")

nonebot.load_plugins("next_bot/plugins")

nonebot.run()
