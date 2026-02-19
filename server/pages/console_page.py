from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_TEMPLATE_DIR = BASE_DIR / "webui" / "templates"


@lru_cache(maxsize=8)
def _load_template(name: str) -> str:
    path = WEBUI_TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def render_login_page(*, next_path: str, error_message: str = "") -> str:
    escaped_next = html.escape(next_path, quote=True)
    escaped_error = html.escape(error_message)
    error_section = ""
    if escaped_error:
        error_section = (
            '<div class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">'
            f"{escaped_error}"
            "</div>"
        )

    template = _load_template("login.html")
    return (
        template.replace("__NEXT_PATH__", escaped_next)
        .replace("__ERROR_SECTION__", error_section)
    )


def render_console_page() -> str:
    return _load_template("app_shell.html")
