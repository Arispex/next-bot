from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from nonebot import get_driver, on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from next_bot.db import Server, get_session
from next_bot.message_parser import parse_command_args_with_fallback
from next_bot.permissions import require_permission
from next_bot.tshock_api import (
    TShockRequestError,
    get_error_reason,
    is_success,
    request_server_api,
)

agent_matcher = on_command("代理")
approve_matcher = on_command("允许执行命令")
reject_matcher = on_command("拒绝执行命令")

AGENT_USAGE = "格式错误，正确格式：代理 <内容>"
APPROVE_USAGE = "格式错误，正确格式：允许执行命令"
REJECT_USAGE = "格式错误，正确格式：拒绝执行命令"


@dataclass
class PendingCommand:
    server_id: int
    command: str


@dataclass
class AgentSession:
    messages: list[dict[str, Any]]
    pending: PendingCommand | None = None
    end_requested: bool = False
    end_summary: str = ""


sessions: dict[str, AgentSession] = {}


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_rawcmd",
            "description": "提议在指定服务器执行一条 TShock 命令。不会实际执行，必须等待用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "integer",
                        "description": "要执行命令的服务器 ID",
                    },
                    "command": {
                        "type": "string",
                        "description": "TShock 命令，示例：/help",
                    },
                    "reason": {
                        "type": "string",
                        "description": "提议该命令的原因",
                    },
                },
                "required": ["server_id", "command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "当任务完成或无需继续时，结束本次会话。",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "结束会话时给用户的简短总结",
                    }
                },
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    },
]
def _get_llm_config() -> tuple[str, str, str]:
    config = get_driver().config
    api_key = str(getattr(config, "llm_api_key", "")).strip()
    model = str(getattr(config, "llm_model", "")).strip()
    base_url = str(
        getattr(
            config,
            "llm_base_url",
            "",
        )
    ).strip()
    return api_key, model, base_url


def _get_servers() -> list[Server]:
    session = get_session()
    try:
        return session.query(Server).order_by(Server.id.asc()).all()
    finally:
        session.close()


def _build_system_prompt(servers: list[Server]) -> str:
    lines = [f"{server.id}. {server.name}" for server in servers]
    servers_text = "\n".join(lines) if lines else "无可用服务器"
    return (
        "你是 Terraria TShock 助手。"
        "你可以通过工具完成任务："
        "1) propose_rawcmd：只能提议命令，等待用户确认后才会执行；"
        "2) end_session：任务完成时结束会话。"
        "不要假装命令已执行。"
        "若需要执行命令，必须先调用 propose_rawcmd。"
        "可用服务器如下：\n"
        f"{servers_text}"
    )


def _get_or_create_session(user_id: str) -> AgentSession:
    existing = sessions.get(user_id)
    if existing is not None:
        return existing

    session = AgentSession(messages=[{"role": "system", "content": _build_system_prompt(_get_servers())}])
    sessions[user_id] = session
    return session


async def _call_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    api_key, model, base_url = _get_llm_config()
    if not api_key:
        raise RuntimeError("missing_api_key")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(base_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("invalid_llm_response")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("invalid_llm_response")
    return message


def _parse_tool_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return {}


def _build_tool_result(ok: bool, message: str, **extra: Any) -> str:
    payload: dict[str, Any] = {"ok": ok, "message": message}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def _find_server(server_id: int) -> Server | None:
    servers = _get_servers()
    return next((server for server in servers if server.id == server_id), None)


def _execute_tool_call(
    session: AgentSession,
    tool_name: str,
    tool_args: dict[str, Any],
) -> str:
    if tool_name == "propose_rawcmd":
        server_id = tool_args.get("server_id")
        command = tool_args.get("command")
        reason = str(tool_args.get("reason", "")).strip()

        if not isinstance(server_id, int):
            return _build_tool_result(False, "server_id 必须是整数")
        if not isinstance(command, str) or not command.strip():
            return _build_tool_result(False, "command 不能为空")
        if _find_server(server_id) is None:
            return _build_tool_result(False, "服务器不存在", server_id=server_id)

        session.pending = PendingCommand(server_id=server_id, command=command.strip())
        return _build_tool_result(
            True,
            "命令提议已创建，等待用户发送「允许执行命令」或「拒绝执行命令」",
            server_id=server_id,
            command=command.strip(),
            reason=reason,
        )

    if tool_name == "end_session":
        summary = tool_args.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return _build_tool_result(False, "summary 不能为空")
        session.end_requested = True
        session.end_summary = summary.strip()
        return _build_tool_result(True, "会话已标记结束", summary=session.end_summary)

    return _build_tool_result(False, f"未知工具：{tool_name}")


async def _run_agent(session: AgentSession) -> str:
    for _ in range(8):
        message = await _call_llm(session.messages)
        content = message.get("content")
        content_text = content.strip() if isinstance(content, str) else ""

        tool_calls = message.get("tool_calls")
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": content if isinstance(content, str) else "",
        }
        if isinstance(tool_calls, list) and tool_calls:
            assistant_message["tool_calls"] = tool_calls
        session.messages.append(assistant_message)

        if isinstance(tool_calls, list) and tool_calls:
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                call_id = call.get("id")
                function_data = call.get("function", {})
                if not isinstance(function_data, dict):
                    continue
                tool_name = function_data.get("name")
                tool_args = _parse_tool_args(function_data.get("arguments"))
                if not isinstance(tool_name, str) or not tool_name:
                    continue

                tool_content = _execute_tool_call(session, tool_name, tool_args)
                tool_message: dict[str, Any] = {
                    "role": "tool",
                    "content": tool_content,
                }
                if isinstance(call_id, str) and call_id:
                    tool_message["tool_call_id"] = call_id
                session.messages.append(tool_message)
            continue

        if content_text:
            return content_text
    return "代理失败，模型未给出有效回复"


def _format_rawcmd_output(response_payload: dict[str, object]) -> str:
    response_value = response_payload.get("response")
    if isinstance(response_value, list):
        lines = [str(item).strip() for item in response_value if str(item).strip()]
        return "\n".join(lines) if lines else "命令已执行，无输出"
    if isinstance(response_value, str) and response_value.strip():
        return response_value.strip()
    return "命令已执行，无输出"


def _finalize_session_if_needed(user_id: str, session: AgentSession) -> str | None:
    if session.end_requested:
        sessions.pop(user_id, None)
        return session.end_summary
    return None


@agent_matcher.handle()
@require_permission("ag.ask")
async def handle_agent(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "代理")
    if not args:
        await bot.send(event, AGENT_USAGE)
        return

    user_id = event.get_user_id()
    session = _get_or_create_session(user_id)
    if session.pending is not None:
        await bot.send(event, "当前有待确认命令，请先发送「允许执行命令」或「拒绝执行命令」")
        return

    user_text = " ".join(args)
    session.messages.append({"role": "user", "content": user_text})

    try:
        reply = await _run_agent(session)
    except RuntimeError as exc:
        if str(exc) == "missing_api_key":
            await bot.send(event, "代理失败，未配置 LLM_API_KEY")
            return
        logger.info(f"代理失败：llm_error={exc}")
        await bot.send(event, "代理失败，模型服务异常")
        return
    except httpx.HTTPError as exc:
        logger.info(f"代理失败：http_error={exc}")
        await bot.send(event, "代理失败，模型服务异常")
        return

    end_summary = _finalize_session_if_needed(user_id, session)
    if end_summary is not None:
        await bot.send(event, end_summary)
        return

    if session.pending is not None:
        pending = session.pending
        logger.info(
            f"代理提议命令：user_id={user_id} server_id={pending.server_id} command={pending.command}"
        )
    await bot.send(event, reply)


@approve_matcher.handle()
@require_permission("ag.approve")
async def handle_approve(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "允许执行命令")
    if args:
        await bot.send(event, APPROVE_USAGE)
        return

    user_id = event.get_user_id()
    session = sessions.get(user_id)
    if session is None or session.pending is None:
        await bot.send(event, "执行失败，没有待确认命令")
        return

    pending = session.pending
    server = _find_server(pending.server_id)
    if server is None:
        session.pending = None
        await bot.send(event, "执行失败，服务器不存在")
        return

    try:
        response = await request_server_api(
            server,
            "/v3/server/rawcmd",
            params={"cmd": pending.command},
        )
    except TShockRequestError:
        result_text = "执行失败，无法连接服务器"
    else:
        if is_success(response):
            result_text = f"执行成功\n{_format_rawcmd_output(response.payload)}"
        else:
            result_text = f"执行失败，{get_error_reason(response)}"

    session.pending = None
    session.messages.append(
        {
            "role": "user",
            "content": (
                "用户已确认执行命令。\n"
                f"执行命令：{pending.command}\n"
                f"执行结果：{result_text}"
            ),
        }
    )

    try:
        reply = await _run_agent(session)
    except Exception as exc:
        logger.info(f"代理执行后回调失败：{exc}")
        await bot.send(event, result_text)
        return

    end_summary = _finalize_session_if_needed(user_id, session)
    if end_summary is not None:
        await bot.send(event, end_summary)
        return

    await bot.send(event, f"{result_text}\n{reply}")


@reject_matcher.handle()
@require_permission("ag.reject")
async def handle_reject(
    bot: Bot, event: Event, arg: Message = CommandArg()
):
    args = parse_command_args_with_fallback(event, arg, "拒绝执行命令")
    if args:
        await bot.send(event, REJECT_USAGE)
        return

    user_id = event.get_user_id()
    session = sessions.get(user_id)
    if session is None or session.pending is None:
        await bot.send(event, "拒绝失败，没有待确认命令")
        return

    session.pending = None
    session.messages.append(
        {"role": "user", "content": "用户拒绝执行该命令，请改用其他方案或结束会话。"}
    )

    try:
        reply = await _run_agent(session)
    except Exception as exc:
        logger.info(f"代理拒绝后回调失败：{exc}")
        await bot.send(event, "已拒绝执行命令")
        return

    end_summary = _finalize_session_if_needed(user_id, session)
    if end_summary is not None:
        await bot.send(event, end_summary)
        return

    await bot.send(event, reply)
