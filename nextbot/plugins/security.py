from __future__ import annotations

from urllib.parse import quote

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from nextbot.command_config import command_control, raise_command_usage
from nextbot.db import Server, User, get_session
from nextbot.message_parser import parse_command_args_with_fallback
from nextbot.permissions import require_permission
from nextbot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

confirm_login_matcher = on_command("允许登入")
reject_login_matcher = on_command("拒绝登入")

_NO_PENDING_MARK = "No pending login request"


def _load_self_and_servers(user_id: str) -> tuple[User | None, list[Server]]:
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        servers = session.query(Server).order_by(Server.id.asc()).all()
        return user, servers
    finally:
        session.close()


async def _broadcast_login_action(
    servers: list[Server], user_name: str, path_template: str
) -> tuple[int, list[tuple[Server, bool, str]]]:
    path = path_template.format(user=quote(user_name, safe=""))
    results: list[tuple[Server, bool, str]] = []
    success_count = 0
    for server in servers:
        try:
            response = await request_server_api(server, path)
        except TShockRequestError:
            results.append((server, False, "无法连接服务器"))
            continue

        if is_success(response):
            success_count += 1
            success_text = str(response.payload.get("response") or "").strip()
            results.append((server, True, success_text))
            continue

        error_text = str(response.payload.get("error") or "").strip()
        if not error_text:
            error_text = get_error_reason(response)
        results.append((server, False, error_text))
    return success_count, results


def _pick_failure_reason(
    action: str, results: list[tuple[Server, bool, str]]
) -> str:
    non_pending_reasons = [
        reason
        for _, ok, reason in results
        if not ok and _NO_PENDING_MARK not in reason
    ]
    if not non_pending_reasons:
        return f"{action}失败，没有待处理的登入请求"
    return f"{action}失败，{non_pending_reasons[0]}"


def _log_results(
    action: str,
    user_id: str,
    user_name: str,
    success_count: int,
    results: list[tuple[Server, bool, str]],
) -> None:
    logger.info(
        f"{action}处理完成：user_id={user_id} name={user_name} "
        f"success={success_count} total={len(results)}"
    )
    for server, ok, reason in results:
        logger.info(
            f"{action}服务器结果：server_id={server.id} name={server.name} "
            f"ok={ok} reason={reason}"
        )


@confirm_login_matcher.handle()
@command_control(
    command_key="security.login.confirm",
    display_name="允许登入",
    permission="security.login.confirm",
    description="允许当前账号的待确认登入请求",
    usage="允许登入",
)
@require_permission("security.login.confirm")
async def handle_confirm_login(
    bot: Bot, event: Event, arg: Message = CommandArg()
) -> None:
    args = parse_command_args_with_fallback(event, arg, "允许登入")
    if args:
        raise_command_usage()

    user_id = event.get_user_id()
    user, servers = _load_self_and_servers(user_id)
    if user is None:
        await bot.send(event, "允许失败，未注册账号")
        return
    if not servers:
        await bot.send(event, "允许失败，暂无服务器")
        return

    success_count, results = await _broadcast_login_action(
        servers, user.name, "/nextbot/security/confirm-login/{user}"
    )
    _log_results("允许登入", user_id, user.name, success_count, results)

    if success_count > 0:
        await bot.send(event, "允许成功，可在 5 分钟内重新连接")
        return

    await bot.send(event, _pick_failure_reason("允许", results))


@reject_login_matcher.handle()
@command_control(
    command_key="security.login.reject",
    display_name="拒绝登入",
    permission="security.login.reject",
    description="拒绝当前账号的待确认登入请求",
    usage="拒绝登入",
)
@require_permission("security.login.reject")
async def handle_reject_login(
    bot: Bot, event: Event, arg: Message = CommandArg()
) -> None:
    args = parse_command_args_with_fallback(event, arg, "拒绝登入")
    if args:
        raise_command_usage()

    user_id = event.get_user_id()
    user, servers = _load_self_and_servers(user_id)
    if user is None:
        await bot.send(event, "拒绝失败，未注册账号")
        return
    if not servers:
        await bot.send(event, "拒绝失败，暂无服务器")
        return

    success_count, results = await _broadcast_login_action(
        servers, user.name, "/nextbot/security/reject-login/{user}"
    )
    _log_results("拒绝登入", user_id, user.name, success_count, results)

    if success_count > 0:
        await bot.send(event, "拒绝成功")
        return

    await bot.send(event, _pick_failure_reason("拒绝", results))
