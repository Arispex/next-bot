from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from nonebot.log import logger

from nextbot.db import Server, Shop, ShopItem, get_session
from nextbot.progression import PROGRESSION_KEY_TO_ZH, TIER_OPTIONS
from server.routes import api_error, api_success, read_json_object

router = APIRouter()

_VALID_KINDS = {"item", "command"}
_NAME_MAX_LEN = 50
_DESC_MAX_LEN = 200
_CMD_MAX_LEN = 500


def _serialize_shop(shop: Shop, *, item_count: int | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": int(shop.id),
        "name": str(shop.name),
        "description": str(shop.description or ""),
        "sort_order": int(shop.sort_order or 0),
        "enabled": bool(shop.enabled),
    }
    if item_count is not None:
        data["item_count"] = int(item_count)
    return data


def _serialize_shop_item(item: ShopItem, *, target_server_label: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": int(item.id),
        "shop_id": int(item.shop_id),
        "sort_order": int(item.sort_order or 0),
        "name": str(item.name),
        "description": str(item.description or ""),
        "kind": str(item.kind),
        "price": int(item.price),
        "enabled": bool(item.enabled),
        "item_id": int(item.item_id or 0),
        "prefix_id": int(item.prefix_id or 0),
        "quantity": int(item.quantity or 1),
        "min_tier": str(item.min_tier or "none"),
        "min_tier_label": PROGRESSION_KEY_TO_ZH.get(str(item.min_tier or "none"), str(item.min_tier or "none")),
        "actual_value": int(item.actual_value) if getattr(item, "actual_value", None) is not None else None,
        "is_mystery": bool(getattr(item, "is_mystery", False)),
        "target_server_id": int(item.target_server_id) if item.target_server_id is not None else None,
        "command_template": str(item.command_template or ""),
        "show_command": bool(getattr(item, "show_command", False)),
        "require_online": bool(getattr(item, "require_online", False)),
    }
    if item.kind == "command":
        if item.target_server_id is None:
            data["target_server_label"] = "全部服务器"
        else:
            data["target_server_label"] = target_server_label or f"#{item.target_server_id}"
    else:
        data["target_server_label"] = ""
    return data


def _validate_shop_payload(
    data: dict[str, Any], *, partial: bool = False,
) -> tuple[dict[str, Any] | None, JSONResponse | None]:
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

    if details:
        return None, api_error(
            status_code=422, code="validation_error", message="参数校验失败", details=details,
        )
    return out, None


def _validate_shop_item_payload(
    data: dict[str, Any],
    *,
    valid_server_ids: set[int],
) -> tuple[dict[str, Any] | None, JSONResponse | None]:
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
        details.append({"field": "kind", "message": "类型必须为 item 或 command"})

    try:
        price = int(data.get("price", -1))
    except (TypeError, ValueError):
        price = -1
    if price < 0:
        details.append({"field": "price", "message": "单价必须为非负整数"})

    try:
        sort_order = int(data.get("sort_order", 0))
    except (TypeError, ValueError):
        sort_order = 0
        details.append({"field": "sort_order", "message": "排序值必须为整数"})

    enabled = bool(data.get("enabled", True))

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

    if details:
        return None, api_error(
            status_code=422, code="validation_error", message="参数校验失败", details=details,
        )

    return {
        "name": name,
        "description": description,
        "kind": kind,
        "price": price,
        "sort_order": sort_order,
        "enabled": enabled,
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
    }, None


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


@router.get("/webui/api/shops/meta/tiers")
async def list_shop_tiers(request: Request) -> JSONResponse:
    return api_success(data=[{"key": key, "label": zh} for key, zh in TIER_OPTIONS])


@router.get("/webui/api/shops/meta/servers")
async def list_shop_servers(request: Request) -> JSONResponse:
    session = get_session()
    try:
        servers = session.query(Server).order_by(Server.id.asc()).all()
        return api_success(
            data=[{"id": int(s.id), "name": str(s.name)} for s in servers],
        )
    finally:
        session.close()


@router.get("/webui/api/shops")
async def list_shops(request: Request) -> JSONResponse:
    session = get_session()
    try:
        shops = session.query(Shop).order_by(Shop.sort_order.asc(), Shop.id.asc()).all()
        counts: dict[int, int] = {}
        if shops:
            for sid, in (
                session.query(ShopItem.shop_id)
                .filter(ShopItem.shop_id.in_([s.id for s in shops]))
                .all()
            ):
                counts[int(sid)] = counts.get(int(sid), 0) + 1
        data = [_serialize_shop(s, item_count=counts.get(int(s.id), 0)) for s in shops]
        return api_success(data=data)
    finally:
        session.close()


@router.post("/webui/api/shops")
async def create_shop(request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    validated, verror = _validate_shop_payload(payload)
    if verror is not None:
        return verror
    assert validated is not None
    if "name" not in validated:
        return api_error(
            status_code=422, code="validation_error", message="参数校验失败",
            details=[{"field": "name", "message": "名称不能为空"}],
        )

    session = get_session()
    try:
        existing = session.query(Shop).filter(Shop.name == validated["name"]).first()
        if existing is not None:
            return api_error(
                status_code=409, code="duplicate_name", message="商店名称已存在",
                details=[{"field": "name", "message": "商店名称已存在"}],
            )
        shop = Shop(
            name=validated["name"],
            description=validated.get("description", ""),
            sort_order=int(validated.get("sort_order", 0)),
            enabled=bool(validated.get("enabled", True)),
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        logger.info(f"WebUI 商店 create：shop_id={shop.id} name={shop.name}")
        return api_success(
            status_code=201,
            data=_serialize_shop(shop, item_count=0),
            headers={"Location": f"/webui/api/shops/{shop.id}"},
        )
    finally:
        session.close()


@router.get("/webui/api/shops/{shop_id}")
async def get_shop(shop_id: int) -> JSONResponse:
    label_map = _load_server_label_map()
    session = get_session()
    try:
        shop = session.query(Shop).filter(Shop.id == shop_id).first()
        if shop is None:
            return api_error(status_code=404, code="not_found", message="商店不存在")
        items = (
            session.query(ShopItem)
            .filter(ShopItem.shop_id == shop_id)
            .order_by(ShopItem.sort_order.asc(), ShopItem.id.asc())
            .all()
        )
        data = _serialize_shop(shop, item_count=len(items))
        data["items"] = [
            _serialize_shop_item(
                it,
                target_server_label=label_map.get(int(it.target_server_id)) if it.target_server_id is not None else None,
            )
            for it in items
        ]
        return api_success(data=data)
    finally:
        session.close()


@router.put("/webui/api/shops/{shop_id}")
async def update_shop(shop_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    validated, verror = _validate_shop_payload(payload, partial=True)
    if verror is not None:
        return verror
    assert validated is not None

    session = get_session()
    try:
        shop = session.query(Shop).filter(Shop.id == shop_id).first()
        if shop is None:
            return api_error(status_code=404, code="not_found", message="商店不存在")
        if "name" in validated and validated["name"] != shop.name:
            dup = session.query(Shop).filter(Shop.name == validated["name"]).first()
            if dup is not None:
                return api_error(
                    status_code=409, code="duplicate_name", message="商店名称已存在",
                    details=[{"field": "name", "message": "商店名称已存在"}],
                )
            shop.name = validated["name"]
        if "description" in validated:
            shop.description = validated["description"]
        if "sort_order" in validated:
            shop.sort_order = int(validated["sort_order"])
        if "enabled" in validated:
            shop.enabled = bool(validated["enabled"])
        session.commit()
        item_count = (
            session.query(ShopItem).filter(ShopItem.shop_id == shop_id).count()
        )
        logger.info(f"WebUI 商店 update：shop_id={shop.id} name={shop.name}")
        return api_success(data=_serialize_shop(shop, item_count=item_count))
    finally:
        session.close()


@router.delete("/webui/api/shops/{shop_id}")
async def delete_shop(shop_id: int) -> JSONResponse:
    session = get_session()
    try:
        shop = session.query(Shop).filter(Shop.id == shop_id).first()
        if shop is None:
            return api_error(status_code=404, code="not_found", message="商店不存在")
        session.query(ShopItem).filter(ShopItem.shop_id == shop_id).delete(
            synchronize_session=False
        )
        session.delete(shop)
        session.commit()
        logger.info(f"WebUI 商店 delete：shop_id={shop_id}")
        return api_success(data={"id": shop_id})
    finally:
        session.close()


@router.post("/webui/api/shops/{shop_id}/items")
async def create_shop_item(shop_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    server_ids = _load_server_id_set()
    validated, verror = _validate_shop_item_payload(payload, valid_server_ids=server_ids)
    if verror is not None:
        return verror
    assert validated is not None

    session = get_session()
    try:
        shop = session.query(Shop).filter(Shop.id == shop_id).first()
        if shop is None:
            return api_error(status_code=404, code="not_found", message="商店不存在")
        item = ShopItem(
            shop_id=shop_id,
            sort_order=validated["sort_order"],
            name=validated["name"],
            description=validated["description"],
            kind=validated["kind"],
            price=validated["price"],
            enabled=validated["enabled"],
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
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        label_map = _load_server_label_map()
        target_label = (
            label_map.get(int(item.target_server_id))
            if item.target_server_id is not None else None
        )
        logger.info(
            f"WebUI 商店商品 create：shop_id={shop_id} item_id={item.id} "
            f"name={item.name} kind={item.kind} price={item.price}"
        )
        return api_success(
            status_code=201,
            data=_serialize_shop_item(item, target_server_label=target_label),
            headers={"Location": f"/webui/api/shops/{shop_id}/items/{item.id}"},
        )
    finally:
        session.close()


@router.put("/webui/api/shops/{shop_id}/items/{item_id}")
async def update_shop_item(shop_id: int, item_id: int, request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error is not None:
        return error
    assert payload is not None

    server_ids = _load_server_id_set()
    validated, verror = _validate_shop_item_payload(payload, valid_server_ids=server_ids)
    if verror is not None:
        return verror
    assert validated is not None

    session = get_session()
    try:
        item = (
            session.query(ShopItem)
            .filter(ShopItem.id == item_id, ShopItem.shop_id == shop_id)
            .first()
        )
        if item is None:
            return api_error(status_code=404, code="not_found", message="商品不存在")
        item.sort_order = validated["sort_order"]
        item.name = validated["name"]
        item.description = validated["description"]
        item.kind = validated["kind"]
        item.price = validated["price"]
        item.enabled = validated["enabled"]
        item.item_id = validated["item_id"]
        item.prefix_id = validated["prefix_id"]
        item.quantity = validated["quantity"]
        item.min_tier = validated["min_tier"]
        item.actual_value = validated["actual_value"]
        item.is_mystery = validated["is_mystery"]
        item.target_server_id = validated["target_server_id"]
        item.command_template = validated["command_template"]
        item.show_command = validated["show_command"]
        item.require_online = validated["require_online"]
        session.commit()
        label_map = _load_server_label_map()
        target_label = (
            label_map.get(int(item.target_server_id))
            if item.target_server_id is not None else None
        )
        logger.info(
            f"WebUI 商店商品 update：shop_id={shop_id} item_id={item.id} "
            f"name={item.name} kind={item.kind} price={item.price}"
        )
        return api_success(data=_serialize_shop_item(item, target_server_label=target_label))
    finally:
        session.close()


@router.delete("/webui/api/shops/{shop_id}/items/{item_id}")
async def delete_shop_item(shop_id: int, item_id: int) -> JSONResponse:
    session = get_session()
    try:
        item = (
            session.query(ShopItem)
            .filter(ShopItem.id == item_id, ShopItem.shop_id == shop_id)
            .first()
        )
        if item is None:
            return api_error(status_code=404, code="not_found", message="商品不存在")
        session.delete(item)
        session.commit()
        logger.info(f"WebUI 商店商品 delete：shop_id={shop_id} item_id={item_id}")
        return api_success(data={"id": item_id})
    finally:
        session.close()
