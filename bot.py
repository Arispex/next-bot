import nonebot
from nonebot.adapters.console import Adapter
from nonebot.log import logger

from next_bot.db import DB_PATH, init_db, ensure_default_groups, get_engine, Base

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

@driver.on_startup
async def _init_database() -> None:
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
