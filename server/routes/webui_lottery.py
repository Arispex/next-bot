from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from nonebot.log import logger

from nextbot.db import LotteryPool, LotteryPrize, Server, get_session
from nextbot.progression import PROGRESSION_KEY_TO_ZH, TIER_OPTIONS
from nextbot.time_utils import beijing_now
from server.routes import api_error, api_success, read_json_object

router = APIRouter()

_VALID_KINDS = {"item", "command", "coin"}
_NAME_MAX_LEN = 50
_DESC_MAX_LEN = 200
_CMD_MAX_LEN = 500
_EXPORT_VERSION = 1
_EXPORT_KIND = "lottery_pools"
_IMPORT_MODES = {"merge", "replace_all"}


def _validation_error_response(details: list[dict[str, str]]) -> JSONResponse:
    return api_error(
        status_code=422, code="validation_error", message="参数校验失败", details=details,
    )


def _serialize_pool(pool: LotteryPool, *, prize_count: int | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": int(pool.id),
        "name": str(pool.name),
        "description": str(pool.description or ""),
        "sort_order": int(pool.sort_order or 0),
        "enabled": bool(pool.enabled),
        "cost_per_draw": int(pool.cost_per_draw or 0),
    }
    if prize_count is not None:
        data["prize_count"] = int(prize_count)
    return data


def _serialize_prize(prize: LotteryPrize, *, target_server_label: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": int(prize.id),
        "pool_id": int(prize.pool_id),
        "sort_order": int(prize.sort_order or 0),
        "name": str(prize.name),
        "description": str(prize.description or ""),
        "kind": str(prize.kind),
        "enabled": bool(prize.enabled),
        "weight": float(prize.weight) if getattr(prize, "weight", None) is not None else None,
        "item_id": int(prize.item_id or 0),
        "prefix_id": int(prize.prefix_id or 0),
        "quantity": int(prize.quantity or 1),
        "min_tier": str(prize.min_tier or "none"),
        "min_tier_label": PROGRESSION_KEY_TO_ZH.get(str(prize.min_tier or "none"), str(prize.min_tier or "none")),
        "actual_value": int(prize.actual_value) if getattr(prize, "actual_value", None) is not None else None,
        "is_mystery": bool(getattr(prize, "is_mystery", False)),
        "target_server_id": int(prize.target_server_id) if prize.target_server_id is not None else None,
        "command_template": str(prize.command_template or ""),
        "show_command": bool(getattr(prize, "show_command", False)),
        "require_online": bool(getattr(prize, "require_online", False)),
        "coin_amount": int(prize.coin_amount or 0),
    }
    if prize.kind == "command":
        if prize.target_server_id is None:
            data["target_server_label"] = "全部服务器"
        else:
            data["target_server_label"] = target_server_label or f"#{prize.target_server_id}"
    else:
        data["target_server_label"] = ""
    return data


def _validate_pool_payload(
    data: dict[str, Any], *, partial: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Validate pool metadata. Returns (validated, []) on success, (None, details) on failure."""
    details: list[dict[str, str]] = []
    out: dict[str, Any] = {}

    if "name" in data or not partial:
        name = str(data.get("name", "")).strip()
        if not name:
            details.append({"field": "name", "message": "名称不能为空"})
        elif len(name) > _NAME_MAX_LEN:
            details.append({"field": "name", "message": f"名称长度不能超过 {_NAME_MAX_LEN}"})
        else:
            out["name"] = name

    if "description" in data:
        desc = str(data.get("description", "")).strip()
        if len(desc) > _DESC_MAX_LEN:
            details.append({"field": "description", "message": f"说明长度不能超过 {_DESC_MAX_LEN}"})
        else:
            out["description"] = desc

    if "sort_order" in data:
        try:
            out["sort_order"] = int(data["sort_order"])
        except (TypeError, ValueError):
            details.append({"field": "sort_order", "message": "排序值必须为整数"})

    if "enabled" in data:
        out["enabled"] = bool(data["enabled"])

    if "cost_per_draw" in data or not partial:
        try:
            cost = int(data.get("cost_per_draw", 0))
        except (TypeError, ValueError):
            cost = -1
        if cost < 0:
            details.append({"field": "cost_per_draw", "message": "抽奖单价必须为非负整数"})
        else:
            out["cost_per_draw"] = cost

    if details:
        return None, details
    return out, []


def _validate_prize_payload(
    data: dict[str, Any],
    *,
    valid_server_ids: set[int],
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    details: list[dict[str, str]] = []

    name = str(data.get("name", "")).strip()
    if not name:
        details.append({"field": "name", "message": "名称不能为空"})
    elif len(name) > _NAME_MAX_LEN:
        details.append({"field": "name", "message": f"名称长度不能超过 {_NAME_MAX_LEN}"})

    description = str(data.get("description", "")).strip()
    if len(description) > _DESC_MAX_LEN:
        details.append({"field": "description", "message": f"说明长度不能超过 {_DESC_MAX_LEN}"})

    kind = str(data.get("kind", "")).strip()
    if kind not in _VALID_KINDS:
        details.append({"field": "kind", "message": "类型必须为 item、command 或 coin"})

    try:
        sort_order = int(data.get("sort_order", 0))
    except (TypeError, ValueError):
        sort_order = 0
        details.append({"field": "sort_order", "message": "排序值必须为整数"})

    enabled = bool(data.get("enabled", True))

    raw_weight = data.get("weight", None)
    if raw_weight is None or (isinstance(raw_weight, str) and raw_weight.strip() == ""):
        weight = None
    else:
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = -1.0
        if weight is not None and (weight < 0.0 or weight > 100.0):
            details.append({"field": "weight", "message": "概率必须为 0-100 之间的数值"})

    item_id = 0
    prefix_id = 0
    quantity = 1
    min_tier = "none"
    actual_value: int | None = None
    is_mystery = False
    target_server_id: int | None = None
    command_template = ""
    show_command = False
    require_online = False
    coin_amount = 0

    if kind == "item":
        try:
            item_id = int(data.get("item_id", 0))
        except (TypeError, ValueError):
            item_id = -1
        if item_id < 1:
            details.append({"field": "item_id", "message": "item_id 必须为正整数"})

        try:
            prefix_id = int(data.get("prefix_id", 0))
        except (TypeError, ValueError):
            prefix_id = -1
        if prefix_id < 0:
            details.append({"field": "prefix_id", "message": "prefix_id 必须为非负整数"})

        try:
            quantity = int(data.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 0
        if quantity < 1:
            details.append({"field": "quantity", "message": "数量必须为正整数"})

        min_tier = str(data.get("min_tier", "none")).strip() or "none"
        if min_tier not in PROGRESSION_KEY_TO_ZH:
            details.append({"field": "min_tier", "message": "进度要求不在已知列表中"})

        raw_actual = data.get("actual_value", None)
        if raw_actual is None or (isinstance(raw_actual, str) and raw_actual.strip() == ""):
            actual_value = None
        else:
            try:
                actual_value = int(raw_actual)
            except (TypeError, ValueError):
                actual_value = -1
            if actual_value is not None and actual_value < 0:
                details.append({"field": "actual_value", "message": "实际单价必须为非负整数"})

        is_mystery = bool(data.get("is_mystery", False))

    if kind == "command":
        raw_target = data.get("target_server_id", None)
        if raw_target is None or (isinstance(raw_target, str) and raw_target.strip() == ""):
            target_server_id = None
        else:
            try:
                target_server_id = int(raw_target)
            except (TypeError, ValueError):
                target_server_id = -1
            if target_server_id is not None and target_server_id not in valid_server_ids:
                details.append({"field": "target_server_id", "message": "目标服务器不存在"})

        command_template = str(data.get("command_template", ""))
        stripped_cmd = command_template.strip()
        if not stripped_cmd:
            details.append({"field": "command_template", "message": "命令模板不能为空"})
        elif len(command_template) > _CMD_MAX_LEN:
            details.append({"field": "command_template", "message": f"命令长度不能超过 {_CMD_MAX_LEN}"})
        else:
            command_template = stripped_cmd

        show_command = bool(data.get("show_command", False))
        require_online = bool(data.get("require_online", False))

    if kind == "coin":
        try:
            coin_amount = int(data.get("coin_amount", 0))
        except (TypeError, ValueError):
            coin_amount = None
            details.append({"field": "coin_amount", "message": "金币数量必须为整数（可正可负）"})
        if coin_amount == 0:
            details.append({"field": "coin_amount", "message": "金币数量不能为 0"})

    if details:
        return None, details

    return {
        "name": name,
        "description": description,
        "kind": kind,
        "sort_order": sort_order,
        "enabled": enabled,
        "weight": weight,
        "item_id": item_id,
        "prefix_id": prefix_id,
        "quantity": quantity,
        "min_tier": min_tier,
        "actual_value": actual_value,
        "is_mystery": is_mystery,
        "target_server_id": target_server_id,
        "command_template": command_template,
        "show_command": show_command,
        "require_online": require_online,
        "coin_amount": coin_amount,
    }, []


def _load_server_id_set() -> set[int]:
    session = get_session()
    try:
        return {int(s.id) for s in session.query(Server).all()}
    finally:
        session.close()


def _load_server_label_map() -> dict[int, str]:
    session = get_session()
    try:
        return {int(s.id): str(s.name) for s in session.query(Server).all()}
    finally:
        session.close()


@router.get("/webui/api/lottery/meta/tiers")
async def list_lottery_tiers(request: Request) -> JSONResponse:
    return api_success(data=[{"key": key, "label": zh} for key, zh in TIER_OPTIONS])


@router.get("/webui/api/lottery/meta/servers")
async def list_lottery_servers(request: Request) -> JSONResponse:
    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
        return api_success(
            data=[{"id": int(s.id), "name": str(s.name)} for s in servers],
        )
    finally:
        session.close()


@router.get("/webui/api/lottery")
async def list_pools(request: Request) -> JSONResponse:
    session = get_session()
    try:
        pools = session.query(LotteryPool).order_by(LotteryPool.sort_order.asc(), LotteryPool.id.asc()).all()
        counts: dict[int, int] = {}
        if pools:
            for pid, in (
                session.query(LotteryPrize.pool_id)
                .filter(LotteryPrize.pool_id.in_([p.id for p in pools]))
                .all()
            ):
                counts[int(pid)] = counts.get(int(pid), 0) + 1
        data = [_serialize_pool(p, prize_count=counts.get(int(p.id), 0)) for p in pools]
        return api_success(data=data)
    finally:
        session.close()


@router.post("/webui/api/lottery")
async def create_pool(request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    validated, details = _validate_pool_payload(payload)
    if details:
        return _validation_error_response(details)
    assert validated is not None
    if "name" not in validated:
        return api_error(
            status_code=422, code="validation_error", message="参数校验失败",
            details=[{"field": "name", "message": "名称不能为空"}],
        )

    session = get_session()
    try:
        existing = session.query(LotteryPool).filter(LotteryPool.name == validated["name"]).first()
        if existing is not None:
            return api_error(
                status_code=409, code="duplicate_name", message="奖池名称已存在",
                details=[{"field": "name", "message": "奖池名称已存在"}],
            )
        pool = LotteryPool(
            name=validated["name"],
            description=validated.get("description", ""),
            sort_order=int(validated.get("sort_order", 0)),
            enabled=bool(validated.get("enabled", True)),
            cost_per_draw=int(validated.get("cost_per_draw", 0)),
        )
        session.add(pool)
        session.commit()
        session.refresh(pool)
        logger.info(f"WebUI 奖池 create：pool_id={pool.id} name={pool.name}")
        return api_success(
            status_code=201,
            data=_serialize_pool(pool, prize_count=0),
            headers={"Location": f"/webui/api/lottery/{pool.id}"},
        )
    finally:
        session.close()

# ---------- Export / Import ----------


def _export_prize_dict(prize: LotteryPrize) -> dict[str, Any]:
    """Return the import-friendly subset of fields for a LotteryPrize."""
    return {
        "name": str(prize.name),
        "description": str(prize.description or ""),
        "kind": str(prize.kind),
        "sort_order": int(prize.sort_order or 0),
        "enabled": bool(prize.enabled),
        "weight": float(prize.weight) if getattr(prize, "weight", None) is not None else None,
        "item_id": int(prize.item_id or 0),
        "prefix_id": int(prize.prefix_id or 0),
        "quantity": int(prize.quantity or 1),
        "min_tier": str(prize.min_tier or "none"),
        "actual_value": int(prize.actual_value) if getattr(prize, "actual_value", None) is not None else None,
        "is_mystery": bool(getattr(prize, "is_mystery", False)),
        "target_server_id": int(prize.target_server_id) if prize.target_server_id is not None else None,
        "command_template": str(prize.command_template or ""),
        "show_command": bool(getattr(prize, "show_command", False)),
        "require_online": bool(getattr(prize, "require_online", False)),
        "coin_amount": int(prize.coin_amount or 0),
    }


@router.get("/webui/api/lottery/export")
async def export_lottery(request: Request) -> JSONResponse:
    session = get_session()
    try:
        pools = (
            session.query(LotteryPool)
            .order_by(LotteryPool.sort_order.asc(), LotteryPool.id.asc())
            .all()
        )
        pool_ids = [int(p.id) for p in pools]
        prizes_by_pool: dict[int, list[LotteryPrize]] = {}
        if pool_ids:
            prizes = (
                session.query(LotteryPrize)
                .filter(LotteryPrize.pool_id.in_(pool_ids))
                .order_by(
                    LotteryPrize.pool_id.asc(),
                    LotteryPrize.sort_order.asc(),
                    LotteryPrize.id.asc(),
                )
                .all()
            )
            for prize in prizes:
                prizes_by_pool.setdefault(int(prize.pool_id), []).append(prize)

        exported: list[dict[str, Any]] = []
        for pool in pools:
            pool_prizes = prizes_by_pool.get(int(pool.id), [])
            exported.append({
                "name": str(pool.name),
                "description": str(pool.description or ""),
                "sort_order": int(pool.sort_order or 0),
                "enabled": bool(pool.enabled),
                "cost_per_draw": int(pool.cost_per_draw or 0),
                "prizes": [_export_prize_dict(p) for p in pool_prizes],
            })

        logger.info(
            f"WebUI 奖池 export：pool_count={len(exported)} "
            f"prize_count={sum(len(p['prizes']) for p in exported)}"
        )
        return api_success(data={
            "version": _EXPORT_VERSION,
            "kind": _EXPORT_KIND,
            "exported_at": beijing_now().isoformat(),
            "pools": exported,
        })
    finally:
        session.close()


@router.post("/webui/api/lottery/import")
async def import_lottery(request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    mode = (request.query_params.get("mode") or "merge").strip() or "merge"
    if mode not in _IMPORT_MODES:
        return api_error(
            status_code=400,
            code="invalid_query_parameter",
            message="mode 必须为 merge 或 replace_all",
            details=[{"field": "mode", "message": "mode 必须为 merge 或 replace_all"}],
        )

    # ---- Top-level structural checks ----
    structural: list[dict[str, str]] = []
    raw_version = payload.get("version")
    if raw_version != _EXPORT_VERSION:
        structural.append({
            "field": "version",
            "message": f"version 必须为 {_EXPORT_VERSION}",
        })
    raw_kind = payload.get("kind")
    if raw_kind not in (None, _EXPORT_KIND):
        structural.append({
            "field": "kind",
            "message": f"kind 必须为 {_EXPORT_KIND}",
        })
    raw_pools = payload.get("pools")
    if not isinstance(raw_pools, list):
        structural.append({"field": "pools", "message": "pools 必须为数组"})
    if structural:
        return _validation_error_response(structural)

    server_ids = _load_server_id_set()

    # ---- Validate every pool + prize, aggregate errors with path prefixes ----
    aggregated: list[dict[str, str]] = []
    validated_pools: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    seen_names: set[str] = set()

    assert isinstance(raw_pools, list)
    for pool_idx, raw_pool in enumerate(raw_pools):
        pool_path = f"pools[{pool_idx}]"
        if not isinstance(raw_pool, dict):
            aggregated.append({"field": pool_path, "message": "必须为对象"})
            continue

        pool_validated, pool_details = _validate_pool_payload(raw_pool)
        if pool_details:
            aggregated.extend({
                "field": f"{pool_path}.{d.get('field', '')}",
                "message": str(d.get("message", "")),
            } for d in pool_details)
            pool_validated = None

        if pool_validated is not None:
            name = str(pool_validated.get("name", ""))
            if name in seen_names:
                aggregated.append({
                    "field": f"{pool_path}.name",
                    "message": f"奖池名称「{name}」在 JSON 中重复",
                })
            else:
                seen_names.add(name)

        raw_prizes = raw_pool.get("prizes", [])
        prizes_validated: list[dict[str, Any]] = []
        if not isinstance(raw_prizes, list):
            aggregated.append({
                "field": f"{pool_path}.prizes",
                "message": "prizes 必须为数组",
            })
            raw_prizes = []

        for prize_idx, raw_prize in enumerate(raw_prizes):
            prize_path = f"{pool_path}.prizes[{prize_idx}]"
            if not isinstance(raw_prize, dict):
                aggregated.append({"field": prize_path, "message": "必须为对象"})
                continue
            prize_validated, prize_details = _validate_prize_payload(
                raw_prize, valid_server_ids=server_ids,
            )
            if prize_details:
                aggregated.extend({
                    "field": f"{prize_path}.{d.get('field', '')}",
                    "message": str(d.get("message", "")),
                } for d in prize_details)
            elif prize_validated is not None:
                prizes_validated.append(prize_validated)

        if pool_validated is not None:
            validated_pools.append((pool_validated, prizes_validated))

    if aggregated:
        return _validation_error_response(aggregated)

    # ---- Apply changes in a single transaction ----
    session = get_session()
    try:
        created = 0
        updated = 0
        prizes_total = 0

        if mode == "replace_all":
            session.query(LotteryPrize).delete(synchronize_session=False)
            session.query(LotteryPool).delete(synchronize_session=False)
            session.flush()

        existing_by_name: dict[str, LotteryPool] = (
            {str(p.name): p for p in session.query(LotteryPool).all()}
            if mode == "merge"
            else {}
        )

        for pool_data, prizes_data in validated_pools:
            name = str(pool_data["name"])
            existing = existing_by_name.get(name)

            if existing is not None:
                if "description" in pool_data:
                    existing.description = pool_data["description"]
                if "sort_order" in pool_data:
                    existing.sort_order = int(pool_data["sort_order"])
                if "enabled" in pool_data:
                    existing.enabled = bool(pool_data["enabled"])
                if "cost_per_draw" in pool_data:
                    existing.cost_per_draw = int(pool_data["cost_per_draw"])
                # Replace all prizes belonging to this pool.
                session.query(LotteryPrize).filter(
                    LotteryPrize.pool_id == existing.id,
                ).delete(synchronize_session=False)
                pool_id = int(existing.id)
                updated += 1
            else:
                pool = LotteryPool(
                    name=name,
                    description=pool_data.get("description", ""),
                    sort_order=int(pool_data.get("sort_order", 0)),
                    enabled=bool(pool_data.get("enabled", True)),
                    cost_per_draw=int(pool_data.get("cost_per_draw", 0)),
                )
                session.add(pool)
                session.flush()
                pool_id = int(pool.id)
                created += 1

            for prize_data in prizes_data:
                session.add(LotteryPrize(
                    pool_id=pool_id,
                    sort_order=int(prize_data["sort_order"]),
                    name=str(prize_data["name"]),
                    description=str(prize_data["description"]),
                    kind=str(prize_data["kind"]),
                    enabled=bool(prize_data["enabled"]),
                    weight=prize_data["weight"],
                    item_id=int(prize_data["item_id"]),
                    prefix_id=int(prize_data["prefix_id"]),
                    quantity=int(prize_data["quantity"]),
                    min_tier=str(prize_data["min_tier"]),
                    actual_value=prize_data["actual_value"],
                    is_mystery=bool(prize_data["is_mystery"]),
                    target_server_id=prize_data["target_server_id"],
                    command_template=str(prize_data["command_template"]),
                    show_command=bool(prize_data["show_command"]),
                    require_online=bool(prize_data["require_online"]),
                    coin_amount=int(prize_data["coin_amount"]),
                ))
                prizes_total += 1

        session.commit()
        logger.info(
            f"WebUI 奖池 import：mode={mode} created={created} updated={updated} "
            f"prizes_total={prizes_total}"
        )
        return api_success(data={
            "mode": mode,
            "created": created,
            "updated": updated,
            "prizes_total": prizes_total,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("/webui/api/lottery/{pool_id}")
async def get_pool(pool_id: int) -> JSONResponse:
    label_map = _load_server_label_map()
    session = get_session()
    try:
        pool = session.query(LotteryPool).filter(LotteryPool.id == pool_id).first()
        if pool is None:
            return api_error(status_code=404, code="not_found", message="奖池不存在")
        prizes = (
            session.query(LotteryPrize)
            .filter(LotteryPrize.pool_id == pool_id)
            .order_by(LotteryPrize.sort_order.asc(), LotteryPrize.id.asc())
            .all()
        )
        data = _serialize_pool(pool, prize_count=len(prizes))
        data["prizes"] = [
            _serialize_prize(
                p,
                target_server_label=label_map.get(int(p.target_server_id)) if p.target_server_id is not None else None,
            )
            for p in prizes
        ]
        return api_success(data=data)
    finally:
        session.close()


@router.put("/webui/api/lottery/{pool_id}")
async def update_pool(pool_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    validated, details = _validate_pool_payload(payload, partial=True)
    if details:
        return _validation_error_response(details)
    assert validated is not None

    session = get_session()
    try:
        pool = session.query(LotteryPool).filter(LotteryPool.id == pool_id).first()
        if pool is None:
            return api_error(status_code=404, code="not_found", message="奖池不存在")
        if "name" in validated and validated["name"] != pool.name:
            dup = session.query(LotteryPool).filter(LotteryPool.name == validated["name"]).first()
            if dup is not None:
                return api_error(
                    status_code=409, code="duplicate_name", message="奖池名称已存在",
                    details=[{"field": "name", "message": "奖池名称已存在"}],
                )
            pool.name = validated["name"]
        if "description" in validated:
            pool.description = validated["description"]
        if "sort_order" in validated:
            pool.sort_order = int(validated["sort_order"])
        if "enabled" in validated:
            pool.enabled = bool(validated["enabled"])
        if "cost_per_draw" in validated:
            pool.cost_per_draw = int(validated["cost_per_draw"])
        session.commit()
        prize_count = (
            session.query(LotteryPrize).filter(LotteryPrize.pool_id == pool_id).count()
        )
        logger.info(f"WebUI 奖池 update：pool_id={pool.id} name={pool.name}")
        return api_success(data=_serialize_pool(pool, prize_count=prize_count))
    finally:
        session.close()


@router.delete("/webui/api/lottery/{pool_id}")
async def delete_pool(pool_id: int) -> JSONResponse:
    session = get_session()
    try:
        pool = session.query(LotteryPool).filter(LotteryPool.id == pool_id).first()
        if pool is None:
            return api_error(status_code=404, code="not_found", message="奖池不存在")
        session.query(LotteryPrize).filter(LotteryPrize.pool_id == pool_id).delete(
            synchronize_session=False
        )
        session.delete(pool)
        session.commit()
        logger.info(f"WebUI 奖池 delete：pool_id={pool_id}")
        return api_success(data={"id": pool_id})
    finally:
        session.close()


@router.post("/webui/api/lottery/{pool_id}/prizes")
async def create_prize(pool_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    server_ids = _load_server_id_set()
    validated, details = _validate_prize_payload(payload, valid_server_ids=server_ids)
    if details:
        return _validation_error_response(details)
    assert validated is not None

    session = get_session()
    try:
        pool = session.query(LotteryPool).filter(LotteryPool.id == pool_id).first()
        if pool is None:
            return api_error(status_code=404, code="not_found", message="奖池不存在")
        prize = LotteryPrize(
            pool_id=pool_id,
            sort_order=validated["sort_order"],
            name=validated["name"],
            description=validated["description"],
            kind=validated["kind"],
            enabled=validated["enabled"],
            weight=validated["weight"],
            item_id=validated["item_id"],
            prefix_id=validated["prefix_id"],
            quantity=validated["quantity"],
            min_tier=validated["min_tier"],
            actual_value=validated["actual_value"],
            is_mystery=validated["is_mystery"],
            target_server_id=validated["target_server_id"],
            command_template=validated["command_template"],
            show_command=validated["show_command"],
            require_online=validated["require_online"],
            coin_amount=validated["coin_amount"],
        )
        session.add(prize)
        session.commit()
        session.refresh(prize)
        label_map = _load_server_label_map()
        target_label = (
            label_map.get(int(prize.target_server_id))
            if prize.target_server_id is not None else None
        )
        logger.info(
            f"WebUI 奖池奖品 create：pool_id={pool_id} prize_id={prize.id} "
            f"name={prize.name} kind={prize.kind} weight={prize.weight}"
        )
        return api_success(
            status_code=201,
            data=_serialize_prize(prize, target_server_label=target_label),
            headers={"Location": f"/webui/api/lottery/{pool_id}/prizes/{prize.id}"},
        )
    finally:
        session.close()


@router.put("/webui/api/lottery/{pool_id}/prizes/{prize_id}")
async def update_prize(pool_id: int, prize_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    server_ids = _load_server_id_set()
    validated, details = _validate_prize_payload(payload, valid_server_ids=server_ids)
    if details:
        return _validation_error_response(details)
    assert validated is not None

    session = get_session()
    try:
        prize = (
            session.query(LotteryPrize)
            .filter(LotteryPrize.id == prize_id, LotteryPrize.pool_id == pool_id)
            .first()
        )
        if prize is None:
            return api_error(status_code=404, code="not_found", message="奖品不存在")
        prize.sort_order = validated["sort_order"]
        prize.name = validated["name"]
        prize.description = validated["description"]
        prize.kind = validated["kind"]
        prize.enabled = validated["enabled"]
        prize.weight = validated["weight"]
        prize.item_id = validated["item_id"]
        prize.prefix_id = validated["prefix_id"]
        prize.quantity = validated["quantity"]
        prize.min_tier = validated["min_tier"]
        prize.actual_value = validated["actual_value"]
        prize.is_mystery = validated["is_mystery"]
        prize.target_server_id = validated["target_server_id"]
        prize.command_template = validated["command_template"]
        prize.show_command = validated["show_command"]
        prize.require_online = validated["require_online"]
        prize.coin_amount = validated["coin_amount"]
        session.commit()
        label_map = _load_server_label_map()
        target_label = (
            label_map.get(int(prize.target_server_id))
            if prize.target_server_id is not None else None
        )
        logger.info(
            f"WebUI 奖池奖品 update：pool_id={pool_id} prize_id={prize.id} "
            f"name={prize.name} kind={prize.kind} weight={prize.weight}"
        )
        return api_success(data=_serialize_prize(prize, target_server_label=target_label))
    finally:
        session.close()


@router.delete("/webui/api/lottery/{pool_id}/prizes/{prize_id}")
async def delete_prize(pool_id: int, prize_id: int) -> JSONResponse:
    session = get_session()
    try:
        prize = (
            session.query(LotteryPrize)
            .filter(LotteryPrize.id == prize_id, LotteryPrize.pool_id == pool_id)
            .first()
        )
        if prize is None:
            return api_error(status_code=404, code="not_found", message="奖品不存在")
        session.delete(prize)
        session.commit()
        logger.info(f"WebUI 奖池奖品 delete：pool_id={pool_id} prize_id={prize_id}")
        return api_success(data={"id": prize_id})
    finally:
        session.close()
