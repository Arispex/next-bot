# Journal - arispex (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-04-10

---



## Session 53: Command aliases, login notify config, daily sign leaderboard

**Date**: 2026-04-10
**Task**: Command aliases, login notify config, daily sign leaderboard

### Summary

(Add summary)

### Main Changes

| Feature | Description |
|---------|-------------|
| Daily sign leaderboard | Added 今日签到排行榜 command showing sign-in order by time (created_at ASC), value displays HH:MM:SS |
| Login notify config | Added LOGIN_NOTIFY_ALL_GROUPS .env setting with WebUI toggle; restricted group lookup to GROUP_ID list only |
| Command aliases | Full custom alias system: DB aliases_json field + migration, startup alias matcher registration, usage message adapts to actual alias typed, WebUI alias editor modal, conflict validation, restart button on commands page, standalone POST /webui/api/restart endpoint |

**Updated Files**:
- `nextbot/db.py` — aliases_json column + migration, leaderboard.daily_sign in guest perms
- `nextbot/command_config.py` — register_alias_matchers, update_command_aliases, _build_usage_message alias support
- `nextbot/plugins/leaderboard.py` — daily sign leaderboard handler
- `bot.py` — startup alias registration, LOGIN_NOTIFY_ALL_GROUPS default
- `server/settings_service.py` — login_notify_all_groups field + _coerce_bool
- `server/routes/webui_commands.py` — PATCH aliases endpoint
- `server/routes/webui_settings.py` — POST /webui/api/restart
- `server/routes/webui_login_requests.py` — multi-group notify + GROUP_ID restriction
- `server/webui/static/js/commands.js` — alias modal + restart button
- `server/webui/templates/commands_content.html` — aliases column + alias modal + restart button
- `server/webui/static/css/commands.css` — btn-danger, action-wrap styles
- `server/webui/static/js/settings.js` — login_notify_all_groups binding
- `server/webui/templates/settings_content.html` — login confirm section


### Git Commits

| Hash | Message |
|------|---------|
| `d290268` | (see git log) |
| `038c737` | (see git log) |
| `1d93501` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 54: 添加关于页面和视频教程链接

**Date**: 2026-04-12
**Task**: 添加关于页面和视频教程链接

### Summary

(Add summary)

### Main Changes

| 改动 | 说明 |
|------|------|
| README 视频教程 | 添加 Bilibili Windows 安装视频教程链接 |
| 关于命令 | 新增「关于」命令，截图渲染项目介绍页面 |
| 关于页面模板 | 双主题 HTML 模板：Hero 区 Logo + 项目名 + 介绍 + 技术栈徽章，项目信息区（作者、仓库、框架、许可证、QQ 交流群），特别感谢区（QQ 头像 + 昵称 + 打码 QQ） |
| Logo 资源路由 | 新增亮/暗两个 Logo 静态资源路由，适配长方形 Logo |
| guest 默认权限 | 添加 about 权限到 guest 组 |

**新增文件**:
- `nextbot/plugins/about.py`
- `server/pages/about_page.py`
- `server/templates/about.html`

**修改文件**:
- `README.md`
- `server/web_server.py`
- `server/routes/render.py`
- `nextbot/db.py`


### Git Commits

| Hash | Message |
|------|---------|
| `2107e4d` | (see git log) |
| `9cda3fc` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 55: 封禁系统、关于页面、签到排名

**Date**: 2026-04-12
**Task**: 封禁系统、关于页面、签到排名

### Summary

(Add summary)

### Main Changes

| 功能 | 说明 |
|------|------|
| README 视频教程 | 添加 Bilibili Windows 安装视频教程链接 |
| 关于页面 | 新增「关于」命令，双主题渲染项目介绍、作者、QQ 交流群、特别感谢（头像 + 打码 QQ） |
| 签到排名 | 签到成功后显示今日签到排名 |
| 封禁用户 | 新增「封禁用户」命令，更新 DB 封禁状态 + 同步所有服务器黑名单 |
| 解封用户 | 新增「解封用户」命令，清除封禁状态 + 移除服务器黑名单 |
| 封禁列表 | 新增「封禁列表」命令，双主题网页渲染，红色系卡片，支持分页 |
| WebUI 封禁 | 用户管理页新增封禁状态列、封禁/解封按钮、封禁 dialog |
| 封禁拦截 | command_control wrapper 统一拦截被封禁用户，回复封禁原因 |
| DB 迁移修复 | bot.py 已有数据库分支补全 ensure_sign_record_schema 和 ensure_user_ban_schema |

**新增文件**:
- `nextbot/plugins/about.py` — 关于命令
- `nextbot/plugins/ban.py` — 封禁/解封/封禁列表命令
- `server/pages/about_page.py` — 关于页面渲染模块
- `server/pages/ban_list_page.py` — 封禁列表渲染模块
- `server/templates/about.html` — 关于页面双主题模板
- `server/templates/ban_list.html` — 封禁列表双主题模板

**修改文件**:
- `nextbot/db.py` — User 新增 is_banned/banned_at/ban_reason + 迁移
- `nextbot/command_config.py` — 封禁拦截逻辑
- `nextbot/plugins/economy.py` — 签到排名
- `bot.py` — 迁移函数调用修复
- `server/web_server.py` — create_about_page + create_ban_list_page
- `server/routes/render.py` — about/ban_list 路由 + logo 资源
- `server/routes/webui_users.py` — 封禁字段序列化 + ban/unban API
- `server/webui/static/js/users.js` — 封禁状态列 + 封禁 dialog
- `server/webui/templates/users_content.html` — 封禁状态表头 + dialog HTML


### Git Commits

| Hash | Message |
|------|---------|
| `2107e4d` | (see git log) |
| `9cda3fc` | (see git log) |
| `2b67a0e` | (see git log) |
| `64441e4` | (see git log) |
| `f69061b` | (see git log) |
| `e6dad1a` | (see git log) |
| `39ada49` | (see git log) |
| `735758b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 56: 封禁安全修复、用户名大小写不敏感、API 全量查询、更改用户名称

**Date**: 2026-04-12
**Task**: 封禁安全修复、用户名大小写不敏感、API 全量查询、更改用户名称

### Summary

(Add summary)

### Main Changes

| 改动 | 说明 |
|------|------|
| Owner 封禁保护 | 封禁命令和 WebUI ban API 新增 Owner 保护，防止封禁 Owner |
| 用户名大小写不敏感 | 全部 5 处 User.name 查询改为 func.lower() 比较 |
| API 全量查询 | GET /webui/api/users 支持 per_page=0 一次性获取全部用户 |
| 更改用户名称 | 新增管理员命令「更改用户名称 <用户/QQ/@> <新名>」 |

**修改文件**:
- `nextbot/plugins/ban.py` — Owner 封禁保护
- `nextbot/plugins/user_manager.py` — 更改用户名称命令 + 用户名大小写不敏感
- `nextbot/message_parser.py` — 用户名解析大小写不敏感
- `server/routes/webui_users.py` — Owner 封禁保护 + 用户名大小写不敏感 + per_page=0
- `server/routes/webui_login_requests.py` — 用户名查找大小写不敏感


### Git Commits

| Hash | Message |
|------|---------|
| `25c15a9` | (see git log) |
| `4d4e7b0` | (see git log) |
| `e0b5aec` | (see git log) |
| `ced5eda` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 57: 抢劫系统、更改用户名称、签到奖励调整

**Date**: 2026-04-12
**Task**: 抢劫系统、更改用户名称、签到奖励调整

### Summary

(Add summary)

### Main Changes

| 功能 | 说明 |
|------|------|
| 抢劫系统 | 新增「抢劫」命令，5 种结果（大成功/成功/失败/反被抢/警察），13 个可配置参数 |
| 抢劫排行榜 | 新增 3 个排行榜：抢劫排行榜（净收入）、被抢排行榜、抢劫成功率排行榜 |
| 更改用户名称 | 新增管理员命令「更改用户名称」，支持用户名/QQ/@用户 |
| 签到奖励调整 | 调整签到默认参数：最大奖励 100、连续签到每日 10、最大连续奖励 140 |

**新增文件**:
- `nextbot/plugins/rob.py` — 抢劫命令

**修改文件**:
- `nextbot/plugins/leaderboard.py` — 3 个抢劫排行榜
- `nextbot/plugins/user_manager.py` — 更改用户名称命令
- `nextbot/plugins/economy.py` — 签到奖励默认值调整
- `nextbot/db.py` — User 新增 5 个抢劫统计字段 + 迁移 + guest 权限
- `bot.py` — ensure_user_rob_schema 注册


### Git Commits

| Hash | Message |
|------|---------|
| `1890c77` | (see git log) |
| `ced5eda` | (see git log) |
| `26dfa6e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
