from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from next_bot.db import Server


class TShockRequestError(Exception):
    pass


@dataclass
class TShockResponse:
    http_status: int
    payload: dict[str, Any]
    api_status: str


async def request_server_api(
    server: Server,
    path: str,
    params: dict[str, str] | None = None,
    *,
    timeout: float = 5.0,
    include_token: bool = True,
) -> TShockResponse:
    request_path = path if path.startswith("/") else f"/{path}"
    query = dict(params or {})
    if include_token and "token" not in query:
        query["token"] = server.key

    url = f"http://{server.ip}:{server.restapi_port}{request_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=query)
    except httpx.RequestError as exc:
        raise TShockRequestError from exc

    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {}

    api_status = str(payload.get("status", "")).strip()
    return TShockResponse(
        http_status=response.status_code,
        payload=payload,
        api_status=api_status,
    )
