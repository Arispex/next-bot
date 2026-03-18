# Error Handling

> How errors are handled in this project.

---

## Overview

FastAPI JSON endpoints in this project use a shared API envelope from `server/routes/__init__.py`.

- Success: `{"data": ...}` and optional `meta`
- Error: `{"error": {"code": ..., "message": ..., "details"?: [...]}}`

Most Web UI CRUD routes follow this pattern:
1. Parse request with `read_json_object(...)` or `read_pagination_query(...)`
2. Normalize / validate fields with small helper functions
3. Return `api_error(...)` for validation or business failures
4. Catch unexpected exceptions, log with `logger.exception(...)`, and return `500 internal_error` with message `"内部错误"`

---

## Shared Helpers

Use the shared helpers in `server/routes/__init__.py` for JSON APIs whenever possible.

- `api_success(...)`
- `api_error(...)`
- `read_json_object(...)`
- `read_pagination_query(...)`
- `build_pagination_meta(...)`
- `build_pagination_slice(...)`

### Examples
- `server/routes/__init__.py` — canonical success/error/request parsing helpers.
- `server/routes/webui_commands.py` — uses `read_json_object(...)`, `api_success(...)`, and `api_error(...)` consistently.
- `server/routes/webui_users.py` — uses shared helpers plus route-local validation translation.

---

## Error Types

The codebase currently uses lightweight custom exceptions instead of a large exception hierarchy.

Common pattern:
- define a route/domain-specific validation exception inheriting from `ValueError`
- attach an optional `field`
- translate it to a `422 validation_error`

### Examples
- `server/routes/webui_users.py` — `UserPayloadValidationError`
- `server/routes/webui_groups.py` — `GroupPayloadValidationError`
- `server/routes/webui_servers.py` — `ServerPayloadValidationError`
- `server/settings_service.py` — `SettingsValidationError`
- `next_bot/command_config.py` — `CommandConfigValidationError`
- `next_bot/tshock_api.py` — `TShockRequestError` for outbound HTTP failures

---

## API Error Responses

### Common status / code mapping in current code
- `400 invalid_json` / `invalid_request_body` — malformed or wrong-shaped JSON body
- `400 invalid_query_parameter` — invalid pagination query values
- `401 unauthorized` — invalid login token
- `404 not_found` — missing resource
- `409 conflict` — duplicate resource or conflicting state
- `422 validation_error` — semantic validation failure
- `500 internal_error` — unexpected exception

### Examples
- `server/routes/webui.py` — session creation returns `422` for empty token and `401` for invalid token.
- `server/routes/webui_commands.py` — maps command validation details to `404`, `409`, or `422`.
- `server/routes/webui_users.py` — returns `409` for duplicate `user_id` / `name`, `422` for invalid group.
- `server/routes/webui_groups.py` — returns `422` for builtin-group delete attempts and bad inheritance.

---

## Error Handling Patterns

### Preferred pattern for JSON write routes
- parse request
- validate inputs with small helper functions
- perform DB or external side effect inside `try`
- `rollback()` on write failure
- `logger.exception(...)` on unexpected errors
- return `api_error(status_code=500, code="internal_error", message="内部错误")`

### Preferred pattern for validation
- normalize one field at a time with private helpers
- raise a domain-specific validation error with `field=...`
- convert that exception into `details=[{"field": ..., "message": ...}]`

### Examples
- `server/routes/webui_users.py` — typical CRUD error pattern.
- `server/routes/webui_groups.py` — field-level validation helpers and error translation.
- `server/routes/webui_servers.py` — validation + DB + external API failure handling.
- `server/settings_service.py` — normalization helpers that raise `SettingsValidationError`.

---

## Special Cases

- Render/static routes may use `HTTPException` directly instead of the JSON envelope.
  - Example: `server/routes/render.py`
- Some business failures are intentionally returned inside a success envelope rather than as an error status.
  - Example: `server/routes/webui_servers.py` returns `reachable: False` in `data` for a failed connectivity test that completed normally.

---

## Common Mistakes

- Do not leak raw exception text to API clients on unexpected failures; return `"内部错误"` instead.
- Do not skip `rollback()` in write-path exception handlers.
- Do not invent a second response envelope for JSON routes; reuse `api_success(...)` / `api_error(...)`.
- Do not assume Pydantic request models are the project norm for these Web UI CRUD routes; current code uses manual validation helpers.
- Broad `except Exception` is common here, but only acceptable when paired with `logger.exception(...)` and a sanitized `500` response.
