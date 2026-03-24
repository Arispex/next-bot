# 更新白名单 REST API 接口

## Goal

将白名单同步从旧的 rawcmd 方式迁移到新的 NextBotAdapter 专用接口。

## 旧接口 vs 新接口

| | 旧 | 新 |
|---|---|---|
| 添加白名单 | `GET /v3/server/rawcmd?cmd=/bwl add {name}` | `GET /nextbot/whitelist/add/{user}` |
| 响应结构 | TShock 标准（含 `status` 字段） | `{ "response": "..." }` 或 `{ "error": "..." }` |

## Requirements

- `_sync_whitelist_to_all_servers` 中的 API 调用从 `/v3/server/rawcmd` 改为 `/nextbot/whitelist/add/{name}`
- 错误处理保持使用 `get_error_reason`

## Files to Modify

- `nextbot/plugins/user_manager.py`
