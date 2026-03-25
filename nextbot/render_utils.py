from __future__ import annotations

from nonebot import get_driver

from nextbot.time_utils import beijing_now


def resolve_render_theme() -> str:
    """读取 render_theme 配置并解析为 dark 或 light。
    auto：北京时间 06:00-20:00 为 light，其余为 dark。
    """
    theme = str(getattr(get_driver().config, "render_theme", "auto")).strip().lower()
    if theme == "auto":
        return "light" if 6 <= beijing_now().hour < 20 else "dark"
    return theme if theme in {"dark", "light"} else "dark"
