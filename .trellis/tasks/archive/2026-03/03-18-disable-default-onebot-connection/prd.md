# Disable default OneBot connection without ONEBOT_WS_URLS

## Goal
When `.env` does not configure `ONEBOT_WS_URLS`, the process should not actively attempt to connect to OneBot. This avoids repeated connection failure logs against the default localhost endpoint.

## Requirements
- Do not inject a default `ONEBOT_WS_URLS` value into newly created `.env` files.
- If `ONEBOT_WS_URLS` is absent or empty at runtime, skip registering the OneBot adapter.
- Keep existing behavior unchanged when `ONEBOT_WS_URLS` is configured.
- Add minimal, useful logs for the skip path without logging secrets.

## Acceptance Criteria
- [ ] A fresh `.env` created by the app no longer contains a default localhost `ONEBOT_WS_URLS` entry.
- [ ] Startup does not attempt OneBot connection when `ONEBOT_WS_URLS` is missing or empty.
- [ ] Startup logs clearly explain that OneBot connection is skipped because no WS URLs are configured.
- [ ] Existing configured OneBot deployments continue to register the adapter normally.

## Technical Notes
- Main behavior is in `bot.py`.
- Runtime config values come from `nonebot.get_driver().config`.
- Logging should follow existing `动作 + 结果 + 关键上下文` style and avoid secret leakage.
