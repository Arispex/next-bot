import random
from datetime import datetime, timedelta

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.command_config import command_control, get_current_param, raise_command_usage
from nextbot.db import User, get_session
from nextbot.message_parser import parse_command_args_with_fallback
from nextbot.permissions import require_permission
from nextbot.time_utils import db_now_utc_naive
from nextbot.text_utils import EMOJI_COIN, EMOJI_GAME, EMOJI_TARGET, reply_block, reply_failure

guess_matcher = on_command("猜数字")

# 用内存记录冷却，重启清零
_cooldown_map: dict[str, datetime] = {}


@guess_matcher.handle()
@command_control(
    command_key="economy.guess_number",
    display_name="猜数字",
    permission="economy.guess_number",
    description="猜数字小游戏，根据猜测与答案的接近程度获得不同倍率奖励",
    usage="猜数字 <猜测数字> <投入金币>",
    params={
        "min_cost": {
            "type": "int",
            "label": "最低投入",
            "description": "最低投入金币数",
            "required": False,
            "default": 10,
            "min": 1,
        },
        "max_cost": {
            "type": "int",
            "label": "最高投入",
            "description": "最高投入金币数，0 表示不限制",
            "required": False,
            "default": 0,
            "min": 0,
        },
        "range_max": {
            "type": "int",
            "label": "数字范围上限",
            "description": "随机数范围为 1 到该值",
            "required": False,
            "default": 100,
            "min": 10,
        },
        "exact_multiplier": {
            "type": "int",
            "label": "命中倍率",
            "description": "猜中答案时的倍率",
            "required": False,
            "default": 10,
            "min": 1,
        },
        "near_range": {
            "type": "int",
            "label": "极近判定范围",
            "description": "与答案差值在此范围内为极近",
            "required": False,
            "default": 5,
            "min": 1,
        },
        "near_multiplier": {
            "type": "int",
            "label": "极近倍率",
            "description": "极近时的倍率",
            "required": False,
            "default": 5,
            "min": 1,
        },
        "close_range": {
            "type": "int",
            "label": "接近判定范围",
            "description": "与答案差值在此范围内为接近",
            "required": False,
            "default": 10,
            "min": 1,
        },
        "close_multiplier": {
            "type": "int",
            "label": "接近倍率",
            "description": "接近时的倍率",
            "required": False,
            "default": 2,
            "min": 1,
        },
        "far_range": {
            "type": "int",
            "label": "偏离判定范围",
            "description": "与答案差值在此范围内为偏离，超出则为远离",
            "required": False,
            "default": 25,
            "min": 1,
        },
        "cooldown_seconds": {
            "type": "int",
            "label": "冷却时间（秒）",
            "description": "两次猜数字之间的最短间隔",
            "required": False,
            "default": 30,
            "min": 0,
        },
    },
    category="小游戏系统",
)
@require_permission("economy.guess_number")
async def handle_guess_number(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))

    args = parse_command_args_with_fallback(event, arg, "猜数字")
    if len(args) != 2:
        raise_command_usage()

    range_max = max(10, int(get_current_param("range_max", 100)))

    try:
        guess = int(args[0])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("猜数字", f"请输入 1-{range_max} 的整数"))
        return
    if guess < 1 or guess > range_max:
        await bot.send(event, at + " " + reply_failure("猜数字", f"数字范围为 1-{range_max}"))
        return

    try:
        cost = int(args[1])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("猜数字", "投入金币必须为正整数"))
        return
    if cost <= 0:
        await bot.send(event, at + " " + reply_failure("猜数字", "投入金币必须为正整数"))
        return

    min_cost = max(1, int(get_current_param("min_cost", 10)))
    max_cost = max(0, int(get_current_param("max_cost", 0)))
    if cost < min_cost:
        await bot.send(event, at + " " + reply_failure("猜数字", f"最低投入 {min_cost} 金币"))
        return
    if max_cost > 0 and cost > max_cost:
        await bot.send(event, at + " " + reply_failure("猜数字", f"最高投入 {max_cost} 金币"))
        return

    user_id = event.get_user_id()

    # 冷却检查
    cooldown_seconds = max(0, int(get_current_param("cooldown_seconds", 30)))
    now = db_now_utc_naive()
    if cooldown_seconds > 0:
        last_time = _cooldown_map.get(user_id)
        if last_time is not None:
            elapsed = now - last_time
            if elapsed < timedelta(seconds=cooldown_seconds):
                remaining = timedelta(seconds=cooldown_seconds) - elapsed
                remaining_s = int(remaining.total_seconds())
                await bot.send(event, at + " " + reply_failure("猜数字", f"冷却中，还需等待 {remaining_s} 秒"))
                return

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            await bot.send(event, at + " " + reply_failure("猜数字", "请先注册账号"))
            return

        coins = int(user.coins or 0)
        if coins < cost:
            await bot.send(event, at + " " + reply_failure("猜数字", f"金币不足（当前 {coins}）"))
            return

        # 生成答案
        answer = random.randint(1, range_max)
        diff = abs(guess - answer)

        # 判定结果
        exact_multiplier = max(1, int(get_current_param("exact_multiplier", 10)))
        near_range = max(1, int(get_current_param("near_range", 5)))
        near_multiplier = max(1, int(get_current_param("near_multiplier", 5)))
        close_range = max(1, int(get_current_param("close_range", 10)))
        close_multiplier = max(1, int(get_current_param("close_multiplier", 2)))
        far_range = max(1, int(get_current_param("far_range", 25)))

        if diff == 0:
            result_type = "命中"
            payout = cost * exact_multiplier
        elif diff <= near_range:
            result_type = "极近"
            payout = cost * near_multiplier
        elif diff <= close_range:
            result_type = "接近"
            payout = cost * close_multiplier
        elif diff <= far_range:
            result_type = "偏离"
            payout = cost // 2
        else:
            result_type = "远离"
            payout = 0

        net = payout - cost
        user.coins = coins + net
        user.guess_total_count = int(user.guess_total_count or 0) + 1
        if net > 0:
            user.guess_win_count = int(user.guess_win_count or 0) + 1
            user.guess_total_gain = int(user.guess_total_gain or 0) + net
        elif net < 0:
            user.guess_total_loss = int(user.guess_total_loss or 0) + abs(net)
        session.commit()

        final_coins = int(user.coins)
    finally:
        session.close()

    _cooldown_map[user_id] = now

    head_emoji = EMOJI_TARGET if diff == 0 else EMOJI_GAME
    lines = [f"🎯 答案 {answer}，你猜 {guess}（差 {diff}）"]
    if net > 0:
        lines.append(f"{EMOJI_COIN} {result_type}！投入 {cost}，获得 {payout}，净赚 {net} 金币")
    elif net == 0:
        lines.append(f"⚖️ {result_type}！投入 {cost} 金币，刚好持平")
    else:
        if payout > 0:
            lines.append(f"❌ {result_type}！投入 {cost}，返还 {payout}，损失 {abs(net)} 金币")
        else:
            lines.append(f"❌ {result_type}！投入 {cost} 金币，全部损失")
    lines.append(f"{EMOJI_COIN} 当前金币：{final_coins}")

    logger.info(
        f"猜数字结果：user_id={user_id} guess={guess} answer={answer} diff={diff} "
        f"result={result_type} cost={cost} payout={payout} net={net}"
    )
    await bot.send(event, at + "\n" + reply_block(f"{head_emoji} 猜数字", lines))
