from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nonebot import get_driver

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
_WRITE_LOCK = threading.RLock()
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_QQ_ID_PATTERN = re.compile(r"^\d{5,20}$")


@dataclass(frozen=True)
class FieldSpec:
    field: str
    env_key: str
    hot_apply: bool
    sensitive: bool = False


@dataclass(frozen=True)
class SaveSettingsResult:
    applied_now_fields: list[str]
    restart_required_fields: list[str]


class SettingsValidationError(ValueError):
    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.field = field


_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("command_start", "COMMAND_START", hot_apply=False),
    FieldSpec("onebot_ws_urls", "ONEBOT_WS_URLS", hot_apply=False),
    FieldSpec("onebot_access_token", "ONEBOT_ACCESS_TOKEN", hot_apply=False, sensitive=True),
    FieldSpec("owner_id", "OWNER_ID", hot_apply=True),
    FieldSpec("group_id", "GROUP_ID", hot_apply=True),
    FieldSpec("web_server_host", "WEB_SERVER_HOST", hot_apply=False),
    FieldSpec("web_server_port", "WEB_SERVER_PORT", hot_apply=False),
    FieldSpec("web_server_public_base_url", "WEB_SERVER_PUBLIC_BASE_URL", hot_apply=True),
    FieldSpec("command_disabled_mode", "COMMAND_DISABLED_MODE", hot_apply=True),
    FieldSpec("command_disabled_message", "COMMAND_DISABLED_MESSAGE", hot_apply=True),
)

_FIELD_BY_NAME: dict[str, FieldSpec] = {item.field: item for item in _FIELD_SPECS}
_FIELD_BY_ENV: dict[str, FieldSpec] = {item.env_key: item for item in _FIELD_SPECS}


def _parse_env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in line:
        return None
    key = line.split("=", 1)[0].strip()
    if not _ENV_KEY_PATTERN.fullmatch(key):
        return None
    return key


def _read_env_lines() -> list[str]:
    if not _ENV_PATH.is_file():
        return []
    return _ENV_PATH.read_text(encoding="utf-8").splitlines()


def _read_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in _read_env_lines():
        key = _parse_env_key(line)
        if key is None:
            continue
        values[key] = line.split("=", 1)[1]
    return values


def _serialize_env_value(field: str, value: Any) -> str:
    if field in {"command_start", "onebot_ws_urls", "owner_id", "group_id"}:
        return json.dumps(value, ensure_ascii=False)
    if field == "web_server_port":
        return str(value)
    return str(value)


def _write_env_values(normalized_values: dict[str, Any]) -> None:
    with _WRITE_LOCK:
        lines = _read_env_lines()
        existing_indices: dict[str, list[int]] = {}

        for index, line in enumerate(lines):
            key = _parse_env_key(line)
            if key in _FIELD_BY_ENV:
                existing_indices.setdefault(key, []).append(index)

        new_lines = list(lines)
        remove_indexes: set[int] = set()
        append_lines: list[str] = []

        for spec in _FIELD_SPECS:
            if spec.field not in normalized_values:
                continue

            env_line = f"{spec.env_key}={_serialize_env_value(spec.field, normalized_values[spec.field])}"
            indices = existing_indices.get(spec.env_key, [])
            if indices:
                new_lines[indices[0]] = env_line
                for idx in indices[1:]:
                    remove_indexes.add(idx)
            else:
                append_lines.append(env_line)

        if remove_indexes:
            new_lines = [
                line for idx, line in enumerate(new_lines)
                if idx not in remove_indexes
            ]

        if append_lines:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.extend(append_lines)

        output = "\n".join(new_lines).rstrip("\n") + "\n"
        temp_path = _ENV_PATH.with_suffix(".env.tmp")
        temp_path.write_text(output, encoding="utf-8")
        temp_path.replace(_ENV_PATH)


def _coerce_string(value: Any, *, field: str, allow_empty: bool = False) -> str:
    text = str(value).strip()
    if not allow_empty and not text:
        raise SettingsValidationError(f"{field} 不能为空", field=field)
    return text


def _coerce_list_of_str(value: Any, *, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise SettingsValidationError(f"{field} 必须是 JSON 数组", field=field)
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if not allow_empty and not text:
            raise SettingsValidationError(f"{field} 不能包含空项", field=field)
        normalized.append(text)
    return normalized


def _coerce_qq_id_list(value: Any, *, field: str) -> list[str]:
    values = _coerce_list_of_str(value, field=field)
    for item in values:
        if _QQ_ID_PATTERN.fullmatch(item) is None:
            raise SettingsValidationError(f"{field} 仅支持 5-20 位数字", field=field)
    return values


def _coerce_ws_urls(value: Any, *, field: str) -> list[str]:
    values = _coerce_list_of_str(value, field=field)
    for item in values:
        parsed = urlparse(item)
        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise SettingsValidationError(f"{field} 必须是 ws/wss URL", field=field)
    return values


def _coerce_http_url(value: Any, *, field: str) -> str:
    text = _coerce_string(value, field=field)
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SettingsValidationError(f"{field} 必须是 http/https URL", field=field)
    return text.rstrip("/")


def _coerce_port(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise SettingsValidationError(f"{field} 必须是整数", field=field)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SettingsValidationError(f"{field} 必须是整数", field=field) from exc
    if parsed < 1 or parsed > 65535:
        raise SettingsValidationError(f"{field} 范围必须在 1-65535", field=field)
    return parsed


def _normalize_field(field: str, value: Any) -> Any:
    if field == "command_start":
        values = _coerce_list_of_str(value, field=field, allow_empty=True)
        if not values:
            raise SettingsValidationError("command_start 至少需要 1 项", field=field)
        return values
    if field == "onebot_ws_urls":
        return _coerce_ws_urls(value, field=field)
    if field == "onebot_access_token":
        return _coerce_string(value, field=field)
    if field == "owner_id":
        return _coerce_qq_id_list(value, field=field)
    if field == "group_id":
        return _coerce_qq_id_list(value, field=field)
    if field == "web_server_host":
        return _coerce_string(value, field=field)
    if field == "web_server_port":
        return _coerce_port(value, field=field)
    if field == "web_server_public_base_url":
        return _coerce_http_url(value, field=field)
    if field == "command_disabled_mode":
        mode = _coerce_string(value, field=field).lower()
        if mode not in {"reply", "silent"}:
            raise SettingsValidationError(
                "command_disabled_mode 仅支持 reply 或 silent",
                field=field,
            )
        return mode
    if field == "command_disabled_message":
        return _coerce_string(value, field=field)
    raise SettingsValidationError("不支持的配置项", field=field)


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in _FIELD_BY_NAME:
            raise SettingsValidationError(f"不允许修改字段：{key}", field=key)
        normalized[key] = _normalize_field(key, value)
    if not normalized:
        raise SettingsValidationError("至少提交一个字段")
    return normalized


def _parse_json_array_env(raw: str, *, field: str) -> list[Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SettingsValidationError(f"{field} 不是有效 JSON 数组", field=field) from exc
    if not isinstance(parsed, list):
        raise SettingsValidationError(f"{field} 必须是 JSON 数组", field=field)
    return parsed


def _load_value_from_env(field: str, raw_value: str) -> Any:
    if field in {"command_start", "onebot_ws_urls", "owner_id", "group_id"}:
        values = _parse_json_array_env(raw_value, field=field)
        return _normalize_field(field, values)
    if field == "web_server_port":
        return _coerce_port(raw_value, field=field)
    return _normalize_field(field, raw_value)


def _load_value_from_config(field: str, config: Any) -> Any:
    raw_value = getattr(config, field, None)
    if field in {"command_start", "onebot_ws_urls", "owner_id", "group_id"}:
        if raw_value is None:
            return []
        if isinstance(raw_value, (set, tuple)):
            raw_value = list(raw_value)
        return _normalize_field(field, raw_value)
    if field == "web_server_port":
        return _coerce_port(raw_value if raw_value is not None else 18081, field=field)
    if field == "web_server_public_base_url" and raw_value is None:
        host = getattr(config, "web_server_host", "127.0.0.1")
        port = getattr(config, "web_server_port", 18081)
        raw_value = f"http://{host}:{port}"
    if field == "command_disabled_mode" and raw_value is None:
        raw_value = "reply"
    if field == "command_disabled_message" and raw_value is None:
        raw_value = "该命令暂时关闭"
    return _normalize_field(field, raw_value if raw_value is not None else "")


def get_settings_snapshot() -> dict[str, Any]:
    env_values = _read_env_values()
    config = get_driver().config
    data: dict[str, Any] = {}
    for spec in _FIELD_SPECS:
        raw = env_values.get(spec.env_key)
        if raw is not None:
            try:
                data[spec.field] = _load_value_from_env(spec.field, raw)
                continue
            except SettingsValidationError:
                pass
        data[spec.field] = _load_value_from_config(spec.field, config)
    return data


def _apply_runtime_updates(values: dict[str, Any]) -> list[str]:
    config = get_driver().config
    applied: list[str] = []
    for spec in _FIELD_SPECS:
        if not spec.hot_apply:
            continue
        if spec.field not in values:
            continue
        setattr(config, spec.field, values[spec.field])
        applied.append(spec.field)
    return applied


def save_settings(payload: dict[str, Any]) -> SaveSettingsResult:
    normalized_values = _normalize_payload(payload)
    _write_env_values(normalized_values)
    applied_now = _apply_runtime_updates(normalized_values)
    restart_required = [
        spec.field
        for spec in _FIELD_SPECS
        if (not spec.hot_apply) and spec.field in normalized_values
    ]
    return SaveSettingsResult(
        applied_now_fields=applied_now,
        restart_required_fields=restart_required,
    )


def get_settings_metadata() -> dict[str, Any]:
    return {
        "hot_apply_fields": [item.field for item in _FIELD_SPECS if item.hot_apply],
        "restart_required_fields": [item.field for item in _FIELD_SPECS if not item.hot_apply],
        "sensitive_fields": [item.field for item in _FIELD_SPECS if item.sensitive],
    }
