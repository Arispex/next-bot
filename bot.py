import nonebot
from nonebot.adapters.console import Adapter

from next_bot.db import DB_PATH, init_db

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

@driver.on_startup
async def _init_database() -> None:
    if not DB_PATH.exists():
        init_db()

nonebot.load_plugins("next_bot/plugins")

nonebot.run()
