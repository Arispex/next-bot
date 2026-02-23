from __future__ import annotations

import html
from pathlib import Path
from typing import Literal


BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_TEMPLATE_DIR = BASE_DIR / "webui" / "templates"
WEBUI_STATIC_DIR = BASE_DIR / "webui" / "static"


def _load_template(name: str) -> str:
    path = WEBUI_TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def _asset_url(path: str) -> str:
    normalized = path.lstrip("/")
    file_path = WEBUI_STATIC_DIR / normalized
    if file_path.is_file():
        version = str(int(file_path.stat().st_mtime))
        return f"/webui/static/{normalized}?v={version}"
    return f"/webui/static/{normalized}"


def _render_app_shell_page(
    *,
    page_title: str,
    active_menu: Literal["dashboard", "commands", "servers"],
    content_template: str,
    page_style_urls: tuple[str, ...] = (),
    page_script_urls: tuple[str, ...] = (),
) -> str:
    base_template = _load_template("app_shell_base.html")
    content_html = _load_template(content_template)
    style_links_html = "\n  ".join(
        f'<link rel="stylesheet" href="{html.escape(url, quote=True)}" />'
        for url in page_style_urls
    )
    script_tags_html = "\n  ".join(
        f'<script src="{html.escape(url, quote=True)}"></script>'
        for url in page_script_urls
    )
    dashboard_active = "is-active" if active_menu == "dashboard" else ""
    commands_active = "is-active" if active_menu == "commands" else ""
    servers_active = "is-active" if active_menu == "servers" else ""

    return (
        base_template.replace("__PAGE_TITLE__", html.escape(page_title))
        .replace("__PAGE_STYLE_LINKS__", style_links_html)
        .replace("__NAV_DASHBOARD_ACTIVE__", dashboard_active)
        .replace("__NAV_COMMANDS_ACTIVE__", commands_active)
        .replace("__NAV_SERVERS_ACTIVE__", servers_active)
        .replace("__MAIN_CONTENT__", content_html)
        .replace(
            "__WEBUI_SCRIPT_URL__",
            html.escape(_asset_url("js/webui.js"), quote=True),
        )
        .replace("__PAGE_SCRIPT_TAGS__", script_tags_html)
    )


def render_login_page(*, next_path: str, error_message: str = "") -> str:
    escaped_next = html.escape(next_path, quote=True)
    escaped_error = html.escape(error_message)
    error_section = ""
    if escaped_error:
        error_section = (
            '<div class="login-error">'
            f"{escaped_error}"
            "</div>"
        )

    template = _load_template("login.html")
    return (
        template.replace("__NEXT_PATH__", escaped_next)
        .replace("__ERROR_SECTION__", error_section)
    )


def render_console_page() -> str:
    return _render_app_shell_page(
        page_title="NextBot WebUI",
        active_menu="dashboard",
        content_template="dashboard_content.html",
        page_style_urls=(
            _asset_url("css/app-shell.css"),
            _asset_url("css/dashboard.css"),
        ),
        page_script_urls=(
            _asset_url("js/dashboard.js"),
        ),
    )


def render_commands_page() -> str:
    return _render_app_shell_page(
        page_title="NextBot Command Config",
        active_menu="commands",
        content_template="commands_content.html",
        page_style_urls=(
            _asset_url("css/app-shell.css"),
            _asset_url("css/commands.css"),
        ),
        page_script_urls=(
            _asset_url("js/commands.js"),
        ),
    )


def render_servers_page() -> str:
    return _render_app_shell_page(
        page_title="NextBot Server Management",
        active_menu="servers",
        content_template="servers_content.html",
        page_style_urls=(
            _asset_url("css/app-shell.css"),
            _asset_url("css/servers.css"),
        ),
        page_script_urls=(
            _asset_url("js/servers.js"),
        ),
    )
