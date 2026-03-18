# Logging Guidelines

> How logging is done in this project.

---

## Overview

This project uses `nonebot.log.logger` across both the bot runtime and the FastAPI Web UI.

Current logging style is:
- mostly Chinese message text
- often followed by key context such as `user_id=...`, `server_id=...`, `reason=...`
- direct `logger.info(...)`, `logger.warning(...)`, `logger.exception(...)` calls in handlers and runtime helpers

There is currently no shared structured logging wrapper, no request ID / trace ID, and no JSON log formatter in the repository.

---

## Log Levels

### `info`
Use for successful normal operations and lifecycle milestones.

Examples:
- `bot.py` — database bootstrap and command sync startup logs
- `server/routes/webui_users.py` — create/update/delete success logs
- `server/routes/webui_groups.py` — CRUD success logs
- `server/routes/webui.py` — successful login session create/delete logs

### `warning`
Use for expected-but-important problems, validation failures, missing resources, auth failures, and business conflicts.

Examples:
- `server/routes/webui.py` — invalid or missing login token
- `server/routes/webui_users.py` — missing user, sync with no servers
- `server/routes/webui_groups.py` — builtin group cannot be deleted
- `server/routes/webui_servers.py` — connectivity test failed or server missing

### `exception`
Use for unexpected exceptions where a traceback is useful.

Examples:
- `server/routes/webui_dashboard.py` — dashboard load failure
- `server/routes/webui_settings.py` — settings save or restart failure
- `server/routes/webui_users.py` — unexpected CRUD exceptions
- `next_bot/signin_reset.py` — background worker failure

---

## Message Style

The current codebase mostly uses this shape:

- Chinese action/result text
- key context appended inline
- optional `reason=...`

Typical examples:
- `创建用户成功：user_id=...，name=...`
- `更新服务器失败：server_id=...，reason=服务器不存在`
- `保存设置失败：field=...，reason=...`

### Good examples in this repo
- `server/routes/webui_users.py`
- `server/routes/webui_groups.py`
- `server/routes/webui_servers.py`
- `bot.py`

Keep new logs close to that style unless the project introduces a shared logging abstraction later.

---

## What to Log

Log these kinds of events:
- startup/bootstrap milestones
- important CRUD success/failure in Web UI APIs
- validation failures that matter for debugging or auditability
- external dependency failures such as TShock API calls
- background worker success/failure
- configuration save / restart scheduling events

### Examples
- `bot.py` — DB initialization and command sync
- `server/routes/webui_settings.py` — save + restart scheduling
- `server/routes/webui_servers.py` — external server connectivity checks
- `next_bot/signin_reset.py` — scheduled reset worker status

---

## What NOT to Log

Avoid logging:
- raw secrets
- access tokens
- cookies
- full request bodies
- full response payloads
- large object dumps

### Important caveat from the current codebase
There is an existing sensitive-data leak example:
- `server/web_server.py` logs `Web UI Token`

Treat that as a **current risk / anti-pattern**, not a pattern to copy.

---

## Common Mistakes

- Do not log secrets or full auth material. The current `Web UI Token` startup log should not be copied into new code.
- Do not add noisy logs inside hot loops or low-value utility functions.
- Do not hand-build a second logging style in one module; stay close to the existing `动作 + 结果 + 关键上下文` pattern.
- Since Uvicorn access logs are disabled in `server/web_server.py`, request-path visibility depends on explicit route logs. Be intentional about adding logs to important HTTP paths.
- Prefer `logger.exception(...)` for unexpected exceptions rather than `logger.error(...)` without traceback.
