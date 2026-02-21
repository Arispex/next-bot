import base64
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from nonebot import get_driver, on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment as OBV11MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from server.screenshot import RenderScreenshotError, ScreenshotOptions, screenshot_url
from server.web_server import create_inventory_page, create_progress_page
from next_bot.command_config import command_control, get_current_param
from next_bot.db import Server, User, get_session
from next_bot.message_parser import (
    parse_command_args_with_fallback,
    parse_command_text_with_fallback,
    resolve_user_id_arg_with_fallback,
)
from next_bot.permissions import require_permission
from next_bot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

online_matcher = on_command("在线")
execute_matcher = on_command("执行")
self_kick_matcher = on_command("自踢")
inventory_matcher = on_command("用户背包")
my_inventory_matcher = on_command("我的背包")
progress_matcher = on_command("进度")

ONLINE_USAGE = "格式错误，正确格式：在线"
EXECUTE_USAGE = "格式错误，正确格式：执行 <服务器 ID> <命令>"
SELF_KICK_USAGE = "格式错误，正确格式：自踢"
INVENTORY_USAGE = "格式错误，正确格式：用户背包 <服务器 ID> <用户 ID/@用户/用户名称>"
MY_INVENTORY_USAGE = "格式错误，正确格式：我的背包 <服务器 ID>"
PROGRESS_USAGE = "格式错误，正确格式：进度 <服务器 ID>"
INVENTORY_SCREENSHOT_OPTIONS = ScreenshotOptions(
    viewport_width=2000,
    viewport_height=1000,
    full_page=True,
)
PROGRESS_SCREENSHOT_OPTIONS = ScreenshotOptions(
    viewport_width=1700,
    viewport_height=700,
    full_page=True,
)
def _parse_execute_arg_text(text: str) -> tuple[int, str] | None:
    if not text:
        return None

    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None

    server_id_text, command = parts
    try:
        server_id = int(server_id_text)
    except ValueError:
        return None

    command_text = command.strip()
    if not command_text:
        return None
    return server_id, command_text


def _extract_response_text(payload: dict[str, object]) -> str:
    value = payload.get("response")
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(lines)
    if isinstance(value, str):
        return value.strip()
    return ""


def _to_non_negative_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _parse_user_info_texts(response_payload: dict[str, object]) -> dict[str, str] | None:
    raw = response_payload.get("response")
    if not isinstance(raw, dict):
        return None

    current_life = _to_non_negative_int(raw.get("当前生命值"))
    max_life = _to_non_negative_int(raw.get("最大生命值"))
    current_mana = _to_non_negative_int(raw.get("当前魔力值"))
    max_mana = _to_non_negative_int(raw.get("最大魔力值"))
    fishing_tasks = _to_non_negative_int(raw.get("渔夫任务数"))
    pve_deaths = _to_non_negative_int(raw.get("PVE死亡次数"))
    pvp_deaths = _to_non_negative_int(raw.get("PVP死亡次数"))
    if (
        current_life is None
        or max_life is None
        or current_mana is None
        or max_mana is None
        or fishing_tasks is None
    ):
        return None

    return {
        "life_text": f"{current_life}/{max_life}",
        "mana_text": f"{current_mana}/{max_mana}",
        "fishing_tasks_text": str(fishing_tasks),
        "pve_deaths_text": str(pve_deaths if pve_deaths is not None else 0),
        "pvp_deaths_text": str(pvp_deaths if pvp_deaths is not None else 0),
    }


def _to_base64_image_uri(path: Path) -> str:
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"base64://{encoded}"


def _to_public_render_url(url: str) -> str:
    config = get_driver().config
    base_url = str(getattr(config, "web_server_public_base_url", "")).strip()
    if not base_url:
        return url

    try:
        target = urlparse(url)
        base = urlparse(base_url)
    except Exception:
        return url

    if not base.scheme or not base.netloc:
        return url

    return urlunparse(
        (
            base.scheme,
            base.netloc,
            target.path,
            target.params,
            target.query,
            target.fragment,
        )
    )


@online_matcher.handle()
@command_control(
    command_key="basic.online",
    display_name="在线",
    permission="bf.online",
    description="查询服务器在线状态与玩家列表",
    params={
        "max_servers": {
            "type": "int",
            "label": "最多展示服务器数",
            "description": "0 表示不限制",
            "default": 0,
            "min": 0,
        }
    },
)
@require_permission("bf.online")
async def handle_online(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "在线")
    if args:
        await bot.send(event, ONLINE_USAGE)
        return

    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    max_servers = get_current_param("max_servers", 0)
    if isinstance(max_servers, int) and max_servers > 0:
        servers = servers[:max_servers]

    if not servers:
        await bot.send(event, "查询失败，暂无服务器")
        return

    lines: list[str] = []
    for server in servers:
        lines.append(f"{server.id}.{server.name}")
        try:
            response = await request_server_api(
                server,
                "/v2/server/status",
                params={"players": "true"},
            )
        except TShockRequestError:
            lines.append("查询失败，无法连接服务器")
            continue

        if not is_success(response):
            lines.append(f"查询失败，{get_error_reason(response)}")
            continue

        players = response.payload.get("players")
        if not isinstance(players, list):
            lines.append("查询失败，返回数据格式错误")
            continue

        playercount = response.payload.get("playercount")
        maxplayers = response.payload.get("maxplayers")
        if not isinstance(playercount, int) or not isinstance(maxplayers, int):
            lines.append("查询失败，返回数据格式错误")
            continue

        if not players:
            lines.append("无玩家在线")
            continue

        lines.append(f"在线玩家({playercount}/{maxplayers})")
        nicknames: list[str] = []
        for player in players:
            if isinstance(player, dict):
                nickname = str(player.get("nickname", "")).strip()
                if nickname:
                    nicknames.append(nickname)
                    continue
            nicknames.append(str(player))

        player_names = ",".join(nicknames)
        lines.append(player_names)

    logger.info(f"在线查询完成：server_count={len(servers)}")
    await bot.send(event, "\n".join(lines))


@execute_matcher.handle()
@command_control(
    command_key="basic.execute",
    display_name="执行",
    permission="bf.exec",
    description="在指定服务器执行原始命令",
)
@require_permission("bf.exec")
async def handle_execute(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    text = parse_command_text_with_fallback(event, arg, "执行")
    parsed = _parse_execute_arg_text(text)
    if parsed is None:
        await bot.send(event, EXECUTE_USAGE)
        return

    target_id, command = parsed
    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == target_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "执行失败，服务器不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v3/server/rawcmd",
            params={"cmd": command},
        )
    except TShockRequestError:
        await bot.send(event, "执行失败，无法连接服务器")
        return

    if not is_success(response):
        await bot.send(event, f"执行失败，{get_error_reason(response)}")
        return

    result_text = _extract_response_text(response.payload)
    if result_text:
        await bot.send(event, f"执行成功，返回内容：\n{result_text}")
        return

    await bot.send(event, "执行成功，无返回内容")


@self_kick_matcher.handle()
@command_control(
    command_key="basic.self_kick",
    display_name="自踢",
    permission="bf.selfkick",
    description="对所有服务器执行当前用户踢出命令",
)
@require_permission("bf.selfkick")
async def handle_self_kick(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "自踢")
    if args:
        await bot.send(event, SELF_KICK_USAGE)
        return

    user_id = event.get_user_id()
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        servers = session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()

    if user is None:
        await bot.send(event, "执行失败，未注册账号")
        return

    if not servers:
        await bot.send(event, "执行失败，暂无服务器")
        return

    lines: list[str] = []
    for server in servers:
        try:
            response = await request_server_api(
                server,
                "/v3/server/rawcmd",
                params={"cmd": f"/kick {user.name}"},
            )
        except TShockRequestError:
            lines.append(f"{server.id}.{server.name}：执行失败，无法连接服务器")
            continue

        if is_success(response):
            lines.append(f"{server.id}.{server.name}：执行成功")
            continue

        reason = get_error_reason(response)
        lines.append(f"{server.id}.{server.name}：执行失败，{reason}")

    logger.info(
        f"自踢执行完成：user_id={user_id} name={user.name} server_count={len(servers)}"
    )
    await bot.send(event, "\n".join(lines))


@inventory_matcher.handle()
@command_control(
    command_key="basic.inventory",
    display_name="用户背包",
    permission="bf.inventory",
    description="查询指定用户背包并生成截图",
)
@require_permission("bf.inventory")
async def handle_user_inventory(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "用户背包")
    if len(args) != 2:
        await bot.send(event, INVENTORY_USAGE)
        return

    try:
        server_id = int(args[0])
    except ValueError:
        await bot.send(event, INVENTORY_USAGE)
        return
    target_user_id, parse_error = resolve_user_id_arg_with_fallback(
        event,
        arg,
        "用户背包",
        arg_index=1,
    )
    if parse_error == "missing":
        await bot.send(event, INVENTORY_USAGE)
        return
    if parse_error == "name_not_found":
        await bot.send(event, "查询失败，用户名称不存在")
        return
    if parse_error == "name_ambiguous":
        await bot.send(event, "查询失败，用户名称不唯一，请使用用户 ID 或 @用户")
        return
    if target_user_id is None:
        await bot.send(event, "查询失败，用户参数解析失败")
        return

    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == server_id).first()
        target_user = session.query(User).filter(User.user_id == target_user_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "查询失败，服务器不存在")
        return
    if target_user is None:
        await bot.send(event, "查询失败，用户不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v2/users/inventory",
            params={"user": target_user.name},
        )
    except TShockRequestError:
        await bot.send(event, "查询失败，无法连接服务器")
        return

    if not is_success(response):
        await bot.send(event, f"查询失败，{get_error_reason(response)}")
        return

    inventory = response.payload.get("response")
    if not isinstance(inventory, list):
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    try:
        info_response = await request_server_api(
            server,
            "/v2/users/info",
            params={"user": target_user.name},
        )
    except TShockRequestError:
        await bot.send(event, "查询失败，无法连接服务器")
        return

    if not is_success(info_response):
        await bot.send(event, f"查询失败，{get_error_reason(info_response)}")
        return

    info_texts = _parse_user_info_texts(info_response.payload)
    if info_texts is None:
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    page_url = create_inventory_page(
        user_id=target_user.user_id,
        user_name=target_user.name,
        server_id=server.id,
        server_name=server.name,
        life_text=info_texts["life_text"],
        mana_text=info_texts["mana_text"],
        fishing_tasks_text=info_texts["fishing_tasks_text"],
        pve_deaths_text=info_texts["pve_deaths_text"],
        pvp_deaths_text=info_texts["pvp_deaths_text"],
        slots=[item for item in inventory if isinstance(item, dict)],
    )
    public_page_url = _to_public_render_url(page_url)
    logger.info(
        "用户背包渲染地址："
        f"server_id={server.id} target_user_id={target_user.user_id} "
        f"internal_url={page_url} public_url={public_page_url}"
    )
    await bot.send(event, f"用户背包链接：{public_page_url}")
    screenshot_path = Path("/tmp") / (
        f"inventory-{server.id}-{target_user.user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    )
    try:
        await screenshot_url(
            page_url,
            screenshot_path,
            options=INVENTORY_SCREENSHOT_OPTIONS,
        )
    except RenderScreenshotError as exc:
        await bot.send(event, f"查询失败，{exc}")
        return

    logger.info(
        f"用户背包截图成功：server_id={server.id} target_user_id={target_user.user_id} file={screenshot_path}"
    )
    if bot.adapter.get_name() == "OneBot V11":
        try:
            image_uri = _to_base64_image_uri(screenshot_path)
        except OSError:
            await bot.send(event, "查询失败，读取截图文件失败")
            return
        await bot.send(event, OBV11MessageSegment.image(file=image_uri))
        return
    await bot.send(event, f"截图成功，文件：{screenshot_path}")


@my_inventory_matcher.handle()
@command_control(
    command_key="basic.my_inventory",
    display_name="我的背包",
    permission="bf.myinventory",
    description="查询当前用户背包并生成截图",
)
@require_permission("bf.myinventory")
async def handle_my_inventory(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "我的背包")
    if len(args) != 1:
        await bot.send(event, MY_INVENTORY_USAGE)
        return

    try:
        server_id = int(args[0])
    except ValueError:
        await bot.send(event, MY_INVENTORY_USAGE)
        return

    user_id = event.get_user_id()
    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == server_id).first()
        user = session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "查询失败，服务器不存在")
        return
    if user is None:
        await bot.send(event, "查询失败，用户不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v2/users/inventory",
            params={"user": user.name},
        )
    except TShockRequestError:
        await bot.send(event, "查询失败，无法连接服务器")
        return

    if not is_success(response):
        await bot.send(event, f"查询失败，{get_error_reason(response)}")
        return

    inventory = response.payload.get("response")
    if not isinstance(inventory, list):
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    try:
        info_response = await request_server_api(
            server,
            "/v2/users/info",
            params={"user": user.name},
        )
    except TShockRequestError:
        await bot.send(event, "查询失败，无法连接服务器")
        return

    if not is_success(info_response):
        await bot.send(event, f"查询失败，{get_error_reason(info_response)}")
        return

    info_texts = _parse_user_info_texts(info_response.payload)
    if info_texts is None:
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    page_url = create_inventory_page(
        user_id=user.user_id,
        user_name=user.name,
        server_id=server.id,
        server_name=server.name,
        life_text=info_texts["life_text"],
        mana_text=info_texts["mana_text"],
        fishing_tasks_text=info_texts["fishing_tasks_text"],
        pve_deaths_text=info_texts["pve_deaths_text"],
        pvp_deaths_text=info_texts["pvp_deaths_text"],
        slots=[item for item in inventory if isinstance(item, dict)],
    )
    public_page_url = _to_public_render_url(page_url)
    logger.info(
        "我的背包渲染地址："
        f"server_id={server.id} user_id={user.user_id} "
        f"internal_url={page_url} public_url={public_page_url}"
    )
    await bot.send(event, f"我的背包链接：{public_page_url}")

    screenshot_path = Path("/tmp") / (
        f"inventory-{server.id}-{user.user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    )
    try:
        await screenshot_url(
            page_url,
            screenshot_path,
            options=INVENTORY_SCREENSHOT_OPTIONS,
        )
    except RenderScreenshotError as exc:
        await bot.send(event, f"查询失败，{exc}")
        return

    logger.info(
        f"我的背包截图成功：server_id={server.id} user_id={user.user_id} file={screenshot_path}"
    )
    if bot.adapter.get_name() == "OneBot V11":
        try:
            image_uri = _to_base64_image_uri(screenshot_path)
        except OSError:
            await bot.send(event, "查询失败，读取截图文件失败")
            return
        await bot.send(event, OBV11MessageSegment.image(file=image_uri))
        return
    await bot.send(event, f"截图成功，文件：{screenshot_path}")


@progress_matcher.handle()
@command_control(
    command_key="basic.progress",
    display_name="进度",
    permission="bf.progress",
    description="查询世界进度并生成截图",
)
@require_permission("bf.progress")
async def handle_world_progress(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "进度")
    if len(args) != 1:
        await bot.send(event, PROGRESS_USAGE)
        return

    try:
        server_id = int(args[0])
    except ValueError:
        await bot.send(event, PROGRESS_USAGE)
        return

    session = get_session()
    try:
        server = session.query(Server).filter(Server.id == server_id).first()
    finally:
        session.close()

    if server is None:
        await bot.send(event, "查询失败，服务器不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v2/world/progress",
        )
    except TShockRequestError:
        await bot.send(event, "查询失败，无法连接服务器")
        return

    if not is_success(response):
        await bot.send(event, f"查询失败，{get_error_reason(response)}")
        return

    progress = response.payload.get("response")
    if not isinstance(progress, dict):
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    normalized_progress: dict[str, object] = {}
    for key, value in progress.items():
        name = str(key).strip()
        if not name:
            continue
        normalized_progress[name] = value

    if not normalized_progress:
        await bot.send(event, "查询失败，返回数据格式错误")
        return

    page_url = create_progress_page(
        server_id=server.id,
        server_name=server.name,
        progress=normalized_progress,
    )
    logger.info(
        "世界进度渲染地址："
        f"server_id={server.id} "
        f"internal_url={page_url}"
    )

    screenshot_path = Path("/tmp") / (
        f"progress-{server.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    )
    try:
        await screenshot_url(
            page_url,
            screenshot_path,
            options=PROGRESS_SCREENSHOT_OPTIONS,
        )
    except RenderScreenshotError as exc:
        await bot.send(event, f"查询失败，{exc}")
        return

    logger.info(
        f"世界进度截图成功：server_id={server.id} file={screenshot_path}"
    )
    if bot.adapter.get_name() == "OneBot V11":
        try:
            image_uri = _to_base64_image_uri(screenshot_path)
        except OSError:
            await bot.send(event, "查询失败，读取截图文件失败")
            return
        await bot.send(event, OBV11MessageSegment.image(file=image_uri))
        return
    await bot.send(event, f"截图成功，文件：{screenshot_path}")
