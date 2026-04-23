from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from nonebot.log import logger

from nextbot.db import WAREHOUSE_CAPACITY, User, WarehouseItem, get_session
from nextbot.progression import PROGRESSION_KEY_TO_ZH, TIER_OPTIONS
from nextbot.time_utils import db_now_utc_naive
from server.routes import api_error, api_success, read_json_object

router = APIRouter()


@router.get("/webui/api/warehouse/tiers")
async def list_tiers(request: Request) -> JSONResponse:
    return api_success(
        data=[{"key": key, "label": zh} for key, zh in TIER_OPTIONS],
    )


@router.get("/webui/api/warehouse")
async def list_warehouse(request: Request) -> JSONResponse:
    user_id = str(request.query_params.get("user_id", "")).strip()
    if not user_id:
        return api_error(
            status_code=400,
            code="invalid_query_parameter",
            message="user_id 不能为空",
            details=[{"field": "user_id", "message": "user_id 不能为空"}],
        )

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return api_error(
                status_code=404, code="user_not_found", message="未找到该用户",
            )
        items = (
            session.query(WarehouseItem)
            .filter(WarehouseItem.user_id == user_id)
            .order_by(WarehouseItem.slot_index.asc())
            .all()
        )
        slots = [
            {
                "slot_index": int(it.slot_index),
                "item_id": int(it.item_id),
                "prefix_id": int(it.prefix_id),
                "quantity": int(it.quantity),
                "min_tier": str(it.min_tier),
                "min_tier_label": PROGRESSION_KEY_TO_ZH.get(str(it.min_tier), str(it.min_tier)),
            }
            for it in items
        ]
    finally:
        session.close()

    return api_success(
        data={
            "user_id": user_id,
            "user_name": str(user.name),
            "capacity": WAREHOUSE_CAPACITY,
            "used": len(slots),
            "slots": slots,
        },
    )


def _validate_slot_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, JSONResponse | None]:
    details: list[dict[str, str]] = []

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
        quantity = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0
    if quantity < 1:
        details.append({"field": "quantity", "message": "quantity 必须为正整数"})

    min_tier = str(data.get("min_tier", "")).strip()
    if min_tier not in PROGRESSION_KEY_TO_ZH:
        details.append({"field": "min_tier", "message": "min_tier 不在进度列表中"})

    if details:
        return None, api_error(
            status_code=422,
            code="validation_error",
            message="参数校验失败",
            details=details,
        )

    return {
        "item_id": item_id,
        "prefix_id": prefix_id,
        "quantity": quantity,
        "min_tier": min_tier,
    }, None


@router.put("/webui/api/warehouse/{user_id}/{slot_index}")
async def upsert_slot(user_id: str, slot_index: int, request: Request) -> JSONResponse:
    if not (1 <= slot_index <= WAREHOUSE_CAPACITY):
        return api_error(
            status_code=400,
            code="invalid_path_parameter",
            message=f"slot_index 必须为 1-{WAREHOUSE_CAPACITY}",
        )

    data, error_response = await read_json_object(request)
    if error_response is not None:
        return error_response
    assert data is not None

    validated, validation_error = _validate_slot_payload(data)
    if validation_error is not None:
        return validation_error
    assert validated is not None

    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return api_error(
                status_code=404, code="user_not_found", message="未找到该用户",
            )
        existing = (
            session.query(WarehouseItem)
            .filter(
                WarehouseItem.user_id == user_id,
                WarehouseItem.slot_index == slot_index,
            )
            .first()
        )
        if existing is None:
            session.add(
                WarehouseItem(
                    user_id=user_id,
                    slot_index=slot_index,
                    item_id=validated["item_id"],
                    prefix_id=validated["prefix_id"],
                    quantity=validated["quantity"],
                    min_tier=validated["min_tier"],
                    created_at=db_now_utc_naive(),
                )
            )
            action = "create"
        else:
            existing.item_id = validated["item_id"]
            existing.prefix_id = validated["prefix_id"]
            existing.quantity = validated["quantity"]
            existing.min_tier = validated["min_tier"]
            action = "update"
        session.commit()
    finally:
        session.close()

    logger.info(
        f"WebUI 仓库 {action}：user_id={user_id} slot={slot_index} "
        f"item={validated['item_id']} qty={validated['quantity']} tier={validated['min_tier']}"
    )
    return api_success(
        data={
            "slot_index": slot_index,
            "item_id": validated["item_id"],
            "prefix_id": validated["prefix_id"],
            "quantity": validated["quantity"],
            "min_tier": validated["min_tier"],
            "min_tier_label": PROGRESSION_KEY_TO_ZH[validated["min_tier"]],
        },
    )


@router.delete("/webui/api/warehouse/{user_id}/{slot_index}")
async def delete_slot(user_id: str, slot_index: int) -> JSONResponse:
    if not (1 <= slot_index <= WAREHOUSE_CAPACITY):
        return api_error(
            status_code=400,
            code="invalid_path_parameter",
            message=f"slot_index 必须为 1-{WAREHOUSE_CAPACITY}",
        )

    session = get_session()
    try:
        existing = (
            session.query(WarehouseItem)
            .filter(
                WarehouseItem.user_id == user_id,
                WarehouseItem.slot_index == slot_index,
            )
            .first()
        )
        if existing is None:
            return api_error(
                status_code=404, code="slot_empty", message="该格子为空",
            )
        session.delete(existing)
        session.commit()
    finally:
        session.close()

    logger.info(f"WebUI 仓库 delete：user_id={user_id} slot={slot_index}")
    return api_success(data={"slot_index": slot_index})
