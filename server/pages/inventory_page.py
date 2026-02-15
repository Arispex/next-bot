from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = BASE_DIR / "server" / "templates" / "inventory.html"


def _normalize_slots(slots: list[dict[str, Any]]) -> list[dict[str, int]]:
    normalized: list[dict[str, int]] = []
    for index in range(350):
        net_id = 0
        prefix_id = 0
        stack = 0
        if index < len(slots) and isinstance(slots[index], dict):
            raw_net_id = slots[index].get("netID", 0)
            raw_prefix_id = slots[index].get("prefix", 0)
            raw_stack = slots[index].get("stack", 0)
            try:
                net_id = int(raw_net_id)
            except (TypeError, ValueError):
                net_id = 0
            try:
                prefix_id = int(raw_prefix_id)
            except (TypeError, ValueError):
                prefix_id = 0
            try:
                stack = int(raw_stack)
            except (TypeError, ValueError):
                stack = 0
        normalized.append(
            {
                "net_id": max(net_id, 0),
                "prefix_id": max(prefix_id, 0),
                "stack": max(stack, 0),
            }
        )
    return normalized


def build_payload(
    *,
    user_id: str,
    user_name: str,
    server_id: int,
    server_name: str,
    slots: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": str(user_id),
        "user_name": str(user_name),
        "server_id": str(server_id),
        "server_name": str(server_name),
        "slots": _normalize_slots(slots),
    }


def render(payload: dict[str, Any]) -> bytes:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = {
        "user_id": payload.get("user_id", ""),
        "user_name": payload.get("user_name", ""),
        "server_id": payload.get("server_id", ""),
        "server_name": payload.get("server_name", ""),
        "generated_at": payload.get("generated_at", ""),
        "slots": payload.get("slots", []),
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    content = template.replace("__INVENTORY_DATA_JSON__", data_json)
    return content.encode("utf-8")
