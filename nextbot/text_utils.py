from __future__ import annotations

# 状态 emoji（固定语义）
STATUS_SUCCESS = "✅"
STATUS_FAILURE = "❌"
STATUS_WARNING = "⚠️"
STATUS_INFO = "ℹ️"
STATUS_HINT = "💡"

# 场景 emoji（按业务复用）
EMOJI_LIST = "📋"
EMOJI_USER = "👤"
EMOJI_GROUP = "👥"
EMOJI_COIN = "💰"
EMOJI_RED_PACKET = "🧧"
EMOJI_GAME = "🎲"
EMOJI_FIRE = "🔥"
EMOJI_TIME = "⏰"
EMOJI_BAN = "🚫"
EMOJI_LOCK = "🔒"
EMOJI_SECURE = "🔐"
EMOJI_SERVER = "🖥️"
EMOJI_TARGET = "🎯"
EMOJI_CHART = "📊"
EMOJI_CALENDAR = "📅"
EMOJI_GUIDE = "📚"
EMOJI_WAREHOUSE = "📦"


def reply_success(action: str, detail: str | None = None) -> str:
    text = f"{STATUS_SUCCESS} {action}成功"
    if detail:
        text += f"，{detail}"
    return text


def reply_failure(action: str, reason: str) -> str:
    return f"{STATUS_FAILURE} {action}失败，{reason}"


def reply_warning(text: str) -> str:
    return f"{STATUS_WARNING} {text}"


def reply_info(text: str) -> str:
    return f"{STATUS_INFO} {text}"


def reply_hint(text: str) -> str:
    return f"{STATUS_HINT} {text}"


def reply_block(
    head: str,
    lines: list[str] | None = None,
    *,
    hint: str | None = None,
) -> str:
    parts = [head]
    if lines:
        parts.extend(lines)
    if hint:
        parts.append(reply_hint(hint))
    return "\n".join(parts)


def reply_list(
    title: str,
    items: list[str],
    *,
    title_emoji: str = EMOJI_LIST,
    hint: str | None = None,
) -> str:
    return reply_block(f"{title_emoji} {title}", items, hint=hint)
