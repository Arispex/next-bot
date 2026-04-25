from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nextbot.time_utils import beijing_now_text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = BASE_DIR / "server" / "templates" / "lottery_result.html"


def _normalize_outcomes(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in outcomes:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind", "")).strip()
        if kind not in {"item", "command", "coin", "miss"}:
            continue
        try:
            count = max(1, int(raw.get("count", 1)))
        except (TypeError, ValueError):
            continue
        entry: dict[str, Any] = {
            "kind": kind,
            "count": count,
            "name": str(raw.get("name", "")).strip(),
            "is_mystery": bool(raw.get("is_mystery", False)),
        }
        if kind == "item":
            try:
                entry["item_id"] = max(0, int(raw.get("item_id", 0)))
                entry["prefix_id"] = max(0, int(raw.get("prefix_id", 0)))
                entry["quantity"] = max(1, int(raw.get("quantity", 1)))
            except (TypeError, ValueError):
                continue
            entry["total_quantity"] = entry["quantity"] * count
        elif kind == "coin":
            try:
                entry["coin_amount"] = int(raw.get("coin_amount", 0))
            except (TypeError, ValueError):
                continue
            entry["total_coin"] = entry["coin_amount"] * count
        out.append(entry)
    return out


def build_payload(
    *,
    pool_id: int,
    pool_name: str,
    user_user_id: str,
    user_user_name: str,
    user_coins_after: int,
    draw_count: int,
    total_cost: int,
    coin_delta: int,
    outcomes: list[dict[str, Any]],
    item_slots_used: int = 0,
    command_results: list[dict[str, Any]] | None = None,
    theme: str = "light",
) -> dict[str, Any]:
    normalized = _normalize_outcomes(outcomes)
    cmd_results = command_results or []
    return {
        "generated_at": beijing_now_text(),
        "pool_id": int(pool_id),
        "pool_name": str(pool_name),
        "user_user_id": str(user_user_id),
        "user_user_name": str(user_user_name),
        "user_coins_after": int(user_coins_after),
        "draw_count": max(1, int(draw_count)),
        "total_cost": int(total_cost),
        "coin_delta": int(coin_delta),
        "outcomes": normalized,
        "item_slots_used": int(item_slots_used),
        "command_results": [
            {
                "server_label": str(r.get("server_label", "")),
                "ok": bool(r.get("ok", False)),
                "reason": str(r.get("reason", "")),
            }
            for r in cmd_results
            if isinstance(r, dict)
        ],
        "theme": str(theme).strip() if str(theme).strip() in {"dark", "light"} else "light",
    }


def render(payload: dict[str, Any]) -> bytes:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = {
        "generated_at": str(payload.get("generated_at", "")),
        "pool_id": int(payload.get("pool_id", 0)),
        "pool_name": str(payload.get("pool_name", "")),
        "user_user_id": str(payload.get("user_user_id", "")),
        "user_user_name": str(payload.get("user_user_name", "")),
        "user_coins_after": int(payload.get("user_coins_after", 0)),
        "draw_count": int(payload.get("draw_count", 1)),
        "total_cost": int(payload.get("total_cost", 0)),
        "coin_delta": int(payload.get("coin_delta", 0)),
        "outcomes": payload.get("outcomes", []),
        "item_slots_used": int(payload.get("item_slots_used", 0)),
        "command_results": payload.get("command_results", []),
        "theme": str(payload.get("theme", "light")),
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    content = template.replace("__LOTTERY_RESULT_DATA_JSON__", data_json)
    return content.encode("utf-8")
