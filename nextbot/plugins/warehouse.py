from __future__ import annotations

import base64
import json
from pathlib import Path

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.command_config import command_control, get_current_param, raise_command_usage
from nextbot.db import WAREHOUSE_CAPACITY, User, WarehouseItem, get_session
from nextbot.message_parser import (
    parse_command_args_with_fallback,
    resolve_user_id_arg_with_fallback,
)
from nextbot.permissions import require_permission
from nextbot.progression import PROGRESSION_KEY_TO_ZH, TIER_OPTIONS, parse_tier
from nextbot.render_utils import resolve_render_theme
from nextbot.text_utils import (
    EMOJI_CHART,
    EMOJI_COIN,
    EMOJI_TARGET,
    EMOJI_USER,
    EMOJI_WAREHOUSE,
    reply_block,
    reply_failure,
    reply_success,
)
from nextbot.time_utils import beijing_filename_timestamp, db_now_utc_naive
from server.screenshot import RenderScreenshotError, ScreenshotOptions, screenshot_url
from server.web_server import create_warehouse_page

WAREHOUSE_SCREENSHOT_OPTIONS = ScreenshotOptions(
    viewport_width=1200,
    viewport_height=1800,
    full_page=True,
)


def _to_base64_image_uri(path: Path) -> str:
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"base64://{encoded}"


_DICTS_DIR = Path(__file__).resolve().parent.parent.parent / "server" / "assets" / "dicts"
_item_name_map: dict[int, str] | None = None
_prefix_name_map: dict[int, str] | None = None


def _load_dict_file(filename: str) -> dict[int, str]:
    path = _DICTS_DIR / filename
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning(f"加载 dict 失败：{path}")
        return {}
    out: dict[int, str] = {}
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            try:
                eid = int(entry.get("id", 0))
            except (TypeError, ValueError):
                continue
            name = str(entry.get("name", "")).strip()
            if eid > 0 and name:
                out[eid] = name
    return out


def _item_display_name(item_id: int) -> str:
    global _item_name_map
    if _item_name_map is None:
        _item_name_map = _load_dict_file("item.json")
    return _item_name_map.get(int(item_id), f"物品ID:{item_id}")


def _prefix_display_name(prefix_id: int) -> str:
    global _prefix_name_map
    if _prefix_name_map is None:
        _prefix_name_map = _load_dict_file("prefix.json")
    if int(prefix_id) <= 0:
        return ""
    return _prefix_name_map.get(int(prefix_id), f"前缀ID:{prefix_id}")


def _format_item_label(item_id: int, prefix_id: int, quantity: int) -> str:
    name = _item_display_name(item_id)
    prefix = _prefix_display_name(prefix_id)
    full = f"{prefix} {name}" if prefix else name
    return f"{full} ×{quantity}"


def _build_tier_options_lines(per_line: int = 4) -> list[str]:
    names = [zh for _, zh in TIER_OPTIONS]
    return ["、".join(names[i:i + per_line]) for i in range(0, len(names), per_line)]


def _load_user(user_id: str) -> User | None:
    session = get_session()
    try:
        return session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close()


def _load_user_by_name(name: str) -> User | None:
    session = get_session()
    try:
        return session.query(User).filter(User.name == name).first()
    finally:
        session.close()


def _load_warehouse_slots(user_id: str) -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.query(WarehouseItem)
            .filter(WarehouseItem.user_id == user_id)
            .order_by(WarehouseItem.slot_index.asc())
            .all()
        )
        return [
            {
                "slot_index": int(r.slot_index),
                "item_id": int(r.item_id),
                "prefix_id": int(r.prefix_id),
                "quantity": int(r.quantity),
                "min_tier": str(r.min_tier),
                "value": int(r.value or 0),
            }
            for r in rows
        ]
    finally:
        session.close()


async def _send_warehouse_image(
    bot: Bot,
    event: Event,
    *,
    page_url: str,
    file_prefix: str,
) -> None:
    screenshot_path = Path("/tmp") / f"{file_prefix}-{beijing_filename_timestamp()}.png"
    try:
        await screenshot_url(
            page_url, screenshot_path, options=WAREHOUSE_SCREENSHOT_OPTIONS,
        )
    except RenderScreenshotError as exc:
        await bot.send(event, reply_failure("查询", str(exc)))
        return

    logger.info(f"仓库截图成功：file={screenshot_path}")
    if bot.adapter.get_name() == "OneBot V11":
        try:
            image_uri = _to_base64_image_uri(screenshot_path)
        except OSError:
            await bot.send(event, reply_failure("查询", "读取截图文件失败"))
            return
        await bot.send(event, OBV11MessageSegment.image(file=image_uri))
        return

    await bot.send(event, f"✅ 截图成功，文件：{screenshot_path}")


list_self_matcher = on_command("我的仓库")
list_user_matcher = on_command("用户仓库")
add_matcher = on_command("添加仓库物品")
remove_matcher = on_command("删除仓库物品")
drop_matcher = on_command("丢弃物品")
recycle_matcher = on_command("回收物品")


@list_self_matcher.handle()
@command_control(
    command_key="warehouse.list_self",
    display_name="我的仓库",
    permission="warehouse.list_self",
    description="查看自己的仓库（网页渲染）",
    usage="我的仓库",
    category="仓库系统",
)
@require_permission("warehouse.list_self")
async def handle_list_self(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    args = parse_command_args_with_fallback(event, arg, "我的仓库")
    if args:
        raise_command_usage()

    user_id = event.get_user_id()
    user = _load_user(user_id)
    if user is None:
        at = OBV11MessageSegment.at(int(user_id))
        await bot.send(event, at + " " + reply_failure("查询", "未注册账号"))
        return

    slots = _load_warehouse_slots(user_id)
    page_url = create_warehouse_page(
        owner_user_id=user_id,
        owner_user_name=str(user.name),
        slots=slots,
        theme=resolve_render_theme(),
    )
    logger.info(
        f"我的仓库渲染：user_id={user_id} used={len(slots)} internal_url={page_url}"
    )
    await _send_warehouse_image(bot, event, page_url=page_url, file_prefix="warehouse-self")


@list_user_matcher.handle()
@command_control(
    command_key="warehouse.list_user",
    display_name="用户仓库",
    permission="warehouse.list_user",
    description="查看指定用户的仓库（网页渲染）",
    usage="用户仓库 <用户名/QQ/@用户>",
    category="仓库系统",
)
@require_permission("warehouse.list_user")
async def handle_list_user(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event, arg, "用户仓库", arg_index=0,
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, reply_failure("查询", "未找到该用户"))
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, reply_failure("查询", "用户名存在重复，请使用 QQ 或 @用户"))
        return
    if parse_error or target_user_id is None:
        raise_command_usage()

    args = parse_command_args_with_fallback(event, arg, "用户仓库")
    if len(args) != 1:
        raise_command_usage()

    user = _load_user(target_user_id)
    if user is None:
        await bot.send(event, reply_failure("查询", "未找到该用户"))
        return

    slots = _load_warehouse_slots(target_user_id)
    page_url = create_warehouse_page(
        owner_user_id=target_user_id,
        owner_user_name=str(user.name),
        slots=slots,
        theme=resolve_render_theme(),
    )
    logger.info(
        f"用户仓库渲染：user_id={target_user_id} used={len(slots)} internal_url={page_url}"
    )
    await _send_warehouse_image(bot, event, page_url=page_url, file_prefix="warehouse-user")


@add_matcher.handle()
@command_control(
    command_key="warehouse.add",
    display_name="添加仓库物品",
    permission="warehouse.add",
    description="将物品添加到指定用户仓库的第一个空格",
    usage="添加仓库物品 <用户名/QQ/@用户> <物品ID> <数量> <前缀ID> <进度> <价值>",
    category="仓库系统",
)
@require_permission("warehouse.add")
async def handle_add(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event, arg, "添加仓库物品", arg_index=0,
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, at + " " + reply_failure("添加", "未找到该用户"))
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, at + " " + reply_failure("添加", "用户名存在重复，请使用 QQ 或 @用户"))
        return
    if parse_error or target_user_id is None:
        raise_command_usage()

    args = parse_command_args_with_fallback(event, arg, "添加仓库物品")
    if len(args) != 6:
        raise_command_usage()

    try:
        item_id = int(args[1])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("添加", "物品 ID 必须为正整数"))
        return
    if item_id < 1:
        await bot.send(event, at + " " + reply_failure("添加", "物品 ID 必须为正整数"))
        return

    try:
        quantity = int(args[2])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("添加", "数量必须为正整数"))
        return
    if quantity < 1:
        await bot.send(event, at + " " + reply_failure("添加", "数量必须为正整数"))
        return

    try:
        prefix_id = int(args[3])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("添加", "前缀 ID 必须为非负整数"))
        return
    if prefix_id < 0:
        await bot.send(event, at + " " + reply_failure("添加", "前缀 ID 必须为非负整数"))
        return

    tier_key = parse_tier(args[4])
    if tier_key is None:
        await bot.send(
            event,
            at + "\n" + reply_block(
                reply_failure("添加", "未知进度"),
                ["📋 可选进度：", *_build_tier_options_lines()],
            ),
        )
        return

    try:
        value = int(args[5])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("添加", "价值必须为非负整数"))
        return
    if value < 0:
        await bot.send(event, at + " " + reply_failure("添加", "价值必须为非负整数"))
        return

    user = _load_user(target_user_id)
    if user is None:
        await bot.send(event, at + " " + reply_failure("添加", "未找到该用户"))
        return

    session = get_session()
    try:
        occupied = {
            int(s) for (s,) in session.query(WarehouseItem.slot_index)
            .filter(WarehouseItem.user_id == target_user_id).all()
        }
        free_slot = next(
            (i for i in range(1, WAREHOUSE_CAPACITY + 1) if i not in occupied),
            None,
        )
        if free_slot is None:
            await bot.send(
                event,
                at + "\n" + reply_block(
                    reply_failure("添加", "仓库已满"),
                    [
                        f"{EMOJI_USER} 用户：{user.name}（{target_user_id}）",
                        f"{EMOJI_CHART} 已使用：{WAREHOUSE_CAPACITY} / {WAREHOUSE_CAPACITY}",
                        "💡 提示：可让用户使用「丢弃物品」或管理员使用「删除仓库物品」释放格子",
                    ],
                ),
            )
            return

        session.add(
            WarehouseItem(
                user_id=target_user_id,
                slot_index=free_slot,
                item_id=item_id,
                prefix_id=prefix_id,
                quantity=quantity,
                min_tier=tier_key,
                value=value,
                created_at=db_now_utc_naive(),
            )
        )
        session.commit()
        used_after = len(occupied) + 1
    finally:
        session.close()

    logger.info(
        f"添加仓库物品成功：target={target_user_id} slot={free_slot} item={item_id} "
        f"prefix={prefix_id} qty={quantity} tier={tier_key} value={value}"
    )
    tier_zh = PROGRESSION_KEY_TO_ZH.get(tier_key, tier_key)
    item_label = _format_item_label(item_id, prefix_id, quantity)
    await bot.send(
        event,
        at + "\n" + reply_block(
            reply_success("添加"),
            [
                f"🎁 物品：{item_label}",
                f"{EMOJI_USER} 用户：{user.name}（{target_user_id}）",
                f"{EMOJI_WAREHOUSE} 格子：#{free_slot}",
                f"{EMOJI_TARGET} 最低进度：{tier_zh}",
                f"{EMOJI_COIN} 单价：{value} 金币",
                f"{EMOJI_CHART} 已使用：{used_after} / {WAREHOUSE_CAPACITY}",
            ],
        ),
    )


@remove_matcher.handle()
@command_control(
    command_key="warehouse.remove",
    display_name="删除仓库物品",
    permission="warehouse.remove",
    description="清空指定用户仓库的指定格子",
    usage="删除仓库物品 <用户名/QQ/@用户> <格子ID>",
    category="仓库系统",
)
@require_permission("warehouse.remove")
async def handle_remove(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    at = OBV11MessageSegment.at(int(event.get_user_id()))

    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event, arg, "删除仓库物品", arg_index=0,
    )
    if parse_error == "missing":
        raise_command_usage()
    if parse_error == "name_not_found":
        await bot.send(event, at + " " + reply_failure("删除", "未找到该用户"))
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, at + " " + reply_failure("删除", "用户名存在重复，请使用 QQ 或 @用户"))
        return
    if parse_error or target_user_id is None:
        raise_command_usage()

    args = parse_command_args_with_fallback(event, arg, "删除仓库物品")
    if len(args) != 2:
        raise_command_usage()

    try:
        slot_index = int(args[1])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("删除", "格子 ID 必须为整数"))
        return
    if not (1 <= slot_index <= WAREHOUSE_CAPACITY):
        await bot.send(
            event,
            at + " " + reply_failure("删除", f"格子 ID 必须为 1-{WAREHOUSE_CAPACITY}"),
        )
        return

    session = get_session()
    try:
        target_user = (
            session.query(User).filter(User.user_id == target_user_id).first()
        )
        item = (
            session.query(WarehouseItem)
            .filter(
                WarehouseItem.user_id == target_user_id,
                WarehouseItem.slot_index == slot_index,
            )
            .first()
        )
        if item is None:
            await bot.send(event, at + " " + reply_failure("删除", "该格子为空"))
            return
        snapshot = (int(item.item_id), int(item.prefix_id), int(item.quantity))
        target_name = str(target_user.name) if target_user is not None else "未知用户"
        session.delete(item)
        session.commit()
        used_after = (
            session.query(WarehouseItem)
            .filter(WarehouseItem.user_id == target_user_id)
            .count()
        )
    finally:
        session.close()

    logger.info(
        f"删除仓库物品成功：target={target_user_id} slot={slot_index} "
        f"item={snapshot[0]} prefix={snapshot[1]} qty={snapshot[2]}"
    )
    await bot.send(
        event,
        at + "\n" + reply_block(
            reply_success("删除"),
            [
                f"🎁 物品：{_format_item_label(*snapshot)}",
                f"{EMOJI_USER} 用户：{target_name}（{target_user_id}）",
                f"{EMOJI_WAREHOUSE} 格子：#{slot_index}",
                f"{EMOJI_CHART} 已使用：{used_after} / {WAREHOUSE_CAPACITY}",
            ],
        ),
    )


@drop_matcher.handle()
@command_control(
    command_key="warehouse.drop_self",
    display_name="丢弃物品",
    permission="warehouse.drop_self",
    description="丢弃自己仓库的指定格子物品",
    usage="丢弃物品 <格子ID>",
    category="仓库系统",
)
@require_permission("warehouse.drop_self")
async def handle_drop(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    user_id = event.get_user_id()
    at = OBV11MessageSegment.at(int(user_id))

    args = parse_command_args_with_fallback(event, arg, "丢弃物品")
    if len(args) != 1:
        raise_command_usage()

    try:
        slot_index = int(args[0])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("丢弃", "格子 ID 必须为整数"))
        return
    if not (1 <= slot_index <= WAREHOUSE_CAPACITY):
        await bot.send(
            event,
            at + " " + reply_failure("丢弃", f"格子 ID 必须为 1-{WAREHOUSE_CAPACITY}"),
        )
        return

    user = _load_user(user_id)
    if user is None:
        await bot.send(event, at + " " + reply_failure("丢弃", "未注册账号"))
        return

    session = get_session()
    try:
        item = (
            session.query(WarehouseItem)
            .filter(
                WarehouseItem.user_id == user_id,
                WarehouseItem.slot_index == slot_index,
            )
            .first()
        )
        if item is None:
            await bot.send(event, at + " " + reply_failure("丢弃", "该格子为空"))
            return
        snapshot = (int(item.item_id), int(item.prefix_id), int(item.quantity))
        session.delete(item)
        session.commit()
        used_after = (
            session.query(WarehouseItem)
            .filter(WarehouseItem.user_id == user_id)
            .count()
        )
    finally:
        session.close()

    logger.info(
        f"丢弃仓库物品成功：user_id={user_id} slot={slot_index} "
        f"item={snapshot[0]} prefix={snapshot[1]} qty={snapshot[2]}"
    )
    await bot.send(
        event,
        at + "\n" + reply_block(
            reply_success("丢弃"),
            [
                f"🎁 物品：{_format_item_label(*snapshot)}",
                f"{EMOJI_WAREHOUSE} 格子：#{slot_index}",
                f"{EMOJI_CHART} 已使用：{used_after} / {WAREHOUSE_CAPACITY}",
            ],
        ),
    )


@recycle_matcher.handle()
@command_control(
    command_key="warehouse.recycle_self",
    display_name="回收物品",
    permission="warehouse.recycle_self",
    description="按价值比例回收自己仓库的物品换金币",
    usage="回收物品 <格子ID>",
    params={
        "recycle_ratio": {
            "type": "float",
            "label": "回收比例",
            "description": "回收时返还价值的比例，0.5 表示返还 50%",
            "required": False,
            "default": 0.5,
            "min": 0.0,
        },
    },
    category="仓库系统",
)
@require_permission("warehouse.recycle_self")
async def handle_recycle(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
    user_id = event.get_user_id()
    at = OBV11MessageSegment.at(int(user_id))

    args = parse_command_args_with_fallback(event, arg, "回收物品")
    if len(args) != 1:
        raise_command_usage()

    try:
        slot_index = int(args[0])
    except ValueError:
        await bot.send(event, at + " " + reply_failure("回收", "格子 ID 必须为整数"))
        return
    if not (1 <= slot_index <= WAREHOUSE_CAPACITY):
        await bot.send(
            event,
            at + " " + reply_failure("回收", f"格子 ID 必须为 1-{WAREHOUSE_CAPACITY}"),
        )
        return

    ratio = max(0.0, float(get_current_param("recycle_ratio", 0.5)))

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            await bot.send(event, at + " " + reply_failure("回收", "未注册账号"))
            return

        item = (
            session.query(WarehouseItem)
            .filter(
                WarehouseItem.user_id == user_id,
                WarehouseItem.slot_index == slot_index,
            )
            .first()
        )
        if item is None:
            await bot.send(event, at + " " + reply_failure("回收", "该格子为空"))
            return

        unit_value = int(item.value or 0)
        quantity = int(item.quantity)
        if unit_value <= 0:
            await bot.send(event, at + " " + reply_failure("回收", "物品无价值，不可回收"))
            return

        snapshot = (int(item.item_id), int(item.prefix_id), quantity)
        refund = int(unit_value * quantity * ratio)

        user.coins = int(user.coins or 0) + refund
        coins_after = int(user.coins)
        session.delete(item)
        session.commit()
        used_after = (
            session.query(WarehouseItem)
            .filter(WarehouseItem.user_id == user_id)
            .count()
        )
    finally:
        session.close()

    logger.info(
        f"回收仓库物品成功：user_id={user_id} slot={slot_index} "
        f"item={snapshot[0]} prefix={snapshot[1]} qty={snapshot[2]} "
        f"unit_value={unit_value} ratio={ratio} refund={refund}"
    )
    await bot.send(
        event,
        at + "\n" + reply_block(
            reply_success("回收"),
            [
                f"🎁 物品：{_format_item_label(*snapshot)}",
                f"{EMOJI_COIN} 单价：{unit_value} 金币",
                f"{EMOJI_CHART} 回收比例：{int(ratio * 100)}%",
                f"{EMOJI_COIN} 获得金币：{refund}",
                f"{EMOJI_COIN} 当前金币：{coins_after}",
                f"{EMOJI_CHART} 已使用：{used_after} / {WAREHOUSE_CAPACITY}",
            ],
        ),
    )
