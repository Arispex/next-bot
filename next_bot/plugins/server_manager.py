from nonebot import on_command
from nonebot.adapters.console import Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.adapters.console.message import MessageSegment


matcher = on_command("test")

@matcher.handle()
async def handle_receive(bot: Bot, event: MessageEvent):
      await bot.send(event, MessageSegment.text("Hello, world!"))