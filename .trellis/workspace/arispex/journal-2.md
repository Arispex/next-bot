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


## Session 58: 新增猜数字/掷骰子排行榜与 v1.1.1 发布

**Date**: 2026-04-20
**Task**: 新增猜数字/掷骰子排行榜与 v1.1.1 发布

### Summary

(Add summary)

### Main Changes

本次会话围绕经济小游戏的统计与排行榜扩展，并完成 v1.1.1 版本发布。

| 改动 | 说明 |
|------|------|
| 经济小游戏落统计 | 猜数字、掷骰子两个小游戏在 `user` 表新增 8 列（`guess_*` / `dice_*` 各 4 列），每次游玩落 total_count / win_count / total_gain / total_loss |
| 新增 4 个排行榜 | 猜数字排行榜、猜数字胜率排行榜、掷骰子排行榜、掷骰子胜率排行榜；净收入榜按 `gain - loss` 排序，胜率榜按 `(win_rate, total_count)` 排序保证 tie-break |
| 胜率榜 value 格式 | 百分比后追加显示 `(胜/总)`，如 `66.7%（6/9）` |
| 抢劫成功率榜 value 格式对齐 | 原有「抢劫成功率排行榜」同步调整格式，与新榜保持一致 |
| 新增 guest 权限 | `leaderboard.dice_income` / `leaderboard.dice_win_rate` / `leaderboard.guess_number_income` / `leaderboard.guess_number_win_rate` |
| 发布 v1.1.1 | 打 tag 并通过 gh CLI 发布 GitHub release，覆盖 v1.1.0 之后 7 个提交（抢劫拆分、WebUI 同步开关、白名单同步、API 错误原因透传、两款小游戏、6 个新榜、格式对齐） |

**Updated Files**:
- `nextbot/db.py`
- `bot.py`
- `nextbot/plugins/dice.py`
- `nextbot/plugins/guess_number.py`
- `nextbot/plugins/leaderboard.py`

**Release**: https://github.com/Arispex/nextbot/releases/tag/v1.1.1


### Git Commits

| Hash | Message |
|------|---------|
| `2d08c13` | (see git log) |
| `fa436a2` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 59: 菜单二级分类重构 + admin 字段清理

**Date**: 2026-04-22
**Task**: 菜单二级分类重构 + admin 字段清理

### Summary

(Add summary)

### Main Changes

本次会话围绕命令菜单可读性，做了一次较大的重构：把单层「菜单 / 管理菜单」改为「菜单（分类列表）+ 菜单 <分类>（命令网格）」二级结构，并把仅服务于旧菜单的 admin 字段全链路下线。

| 改动 | 说明 |
|------|------|
| DB schema | `command_config` 新增 `category` 列（migration `ALTER TABLE ADD COLUMN`），删除 `admin` 列（model 层移除，旧库孤儿列保留） |
| 装饰器 | `@command_control(category="X")` 新参数，`admin=` 参数下线；`RegisteredCommand` / `RuntimeCommandState` dataclass 同步加 category 删 admin；`_build_meta_hash` 把 category 纳入哈希 |
| 同步 / 缓存 | `sync_registered_commands_to_db`、`_to_runtime_state`、`_get_runtime_state`、`_serialize_runtime_state`、`update_command_config` 全链路 add category / drop admin |
| 命令分类 | 65 处 `@command_control` 调用通过脚本批量打上 9 个分类标签：关于 / 用户系统 / 经济系统 / 红包系统 / 排行榜 / 服务器系统 / 安全管理 / 权限管理 / 系统功能；同时 22 处 `admin=True` 一起删除 |
| 菜单插件重写 | 删 `管理菜单` matcher + handler；`菜单`（无参）→ 文本回复分类列表，`菜单 1` / `菜单 红包系统` → 该分类下命令的截图（复用现有 menu_page 渲染） |
| 默认权限 | guest 默认权限串移除 `menu.admin` |
| WebUI | 命令管理页表格列「归属菜单」改为「分类」，删除 admin 切换组件改为只读分类文本；PATCH endpoint 删除 admin 字段；JS `saveSingleCommand` 同步删 admin 参数 |

**Updated Files**:
- `nextbot/db.py` — CommandConfig category 列 + 删 admin 列 + migration
- `nextbot/command_config.py` — 装饰器 / dataclass / sync / cache 链路
- `nextbot/plugins/menu.py` — 二级菜单实现
- `nextbot/plugins/{about,ban,dice,economy,group_manager,guess_number,leaderboard,permission_manager,player_query,red_packet,rob,security,server_manager,server_send,server_tools,user_manager}.py` — 65 处 category= 添加 + 22 处 admin=True 删除
- `server/routes/webui_commands.py` — PATCH 删除 admin
- `server/webui/templates/commands_content.html` — 列头改分类
- `server/webui/static/js/commands.js` — 列渲染 + saveSingleCommand


### Git Commits

| Hash | Message |
|------|---------|
| `eb9e0e0` | (see git log) |
| `7ac1889` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 60: Warehouse system + tutorial command + reply layout standardization

**Date**: 2026-04-23
**Task**: Warehouse system + tutorial command + reply layout standardization

### Summary

(Add summary)

### Main Changes

| 主题 | 说明 |
|---------|-------------|
| 仓库系统 4 期 | 完整建仓 → 物品价值 + 回收 → 批量操作 + 部分数量 → 服务器投递（领取物品） |
| 仓库安全审计 | 修复 4 个漏洞：领取双花 race、添加满仓 IntegrityError、领取多格中途崩溃丢原子性、min_tier 空串绕过 |
| 使用教程命令 | 全新 `使用教程` 命令 + `新手教程` 内置教程，仿菜单两级分发，网页渲染含 QQ 聊天模拟块 |
| 回复风格统一 | 11+ 个 admin/系统命令统一为多行 + 字段 emoji 模板（`@用户` 独占行 + `✅ 动作成功` + 字段行） |
| 红包图片化 | `我的红包` / `红包列表` 改图片渲染 + 分页 + 单价 / 份数 / 红金主题视觉 |

**仓库系统架构**

| 层 | 入口 |
|---|---|
| 数据 | `nextbot/db.py` `WarehouseItem`（user_id, slot_index 1-100, item_id, prefix_id, quantity, min_tier, value, created_at）+ `WAREHOUSE_CAPACITY=100` + `ensure_warehouse_schema()` 迁移 |
| 进度档位 | `nextbot/progression.py`（21 个 boss + `none` 总 22 档；`PROGRESSION_KEY_TO_ZH` / `TIER_OPTIONS` / `parse_tier`） |
| 命令 | `nextbot/plugins/warehouse.py` 7 个 matcher：`我的仓库`、`用户仓库`、`添加仓库物品`、`删除仓库物品`、`丢弃物品`、`回收物品`、`领取物品` |
| 渲染 | `server/pages/warehouse_page.py` + `server/templates/warehouse.html`（红金 10×10 网格，3:4 卡片显示 #ID + 图标 + 前缀 + 名称 + tier chip + 💰 单价） |
| WebUI | `/webui/warehouse?user_id=X` + 用户搜索下拉 + 模态编辑（含 value）+ 用户管理页"仓库"按钮跳转 |
| API | `/webui/api/warehouse{tiers,?user_id,/{uid}/{slot}}` GET / PUT / DELETE |
| 权限 | guest 默认含 `warehouse.list_self/list_user/drop_self/recycle_self/claim_self`；admin 含 `add/remove` |
| 并发安全 | `_warehouse_lock(user_id)` 全局 dict[user_id → asyncio.Lock]；5 个 dispatcher 全部 `async with` |

**关键设计决策**

- **min_tier 实时判定**：不存 server.tier，每次领取查 `/nextbot/world/progress` 比对 `item.min_tier`，跟随实际游戏状态
- **值语义按"单价"**：`value` 表示每件物品金币，回收 = `int(value × quantity × ratio)`，admin 填一次即可
- **格子表达式**：`5` / `1-10` / `1,3,5` / `1-3,5,7-9` / `全部` `all` 五种形式，多格禁用 `[数量]` 参数
- **领取流程**：解析 → 注册 → 服务器存在 → 玩家在线（`/v2/server/status`）→ 进度通过 → `/give <itemId> <name> <qty> [prefix]` → 扣仓库（per-slot commit 防崩溃丢原子性）
- **回复模板**：`@用户\n✅ 动作成功\n🎁 物品: ...\n👤 用户: ...\n📦 格子: ...\n📊 已使用: N/100` 全套统一

**Updated Files** (主要新建/修改):
- 新建：`nextbot/progression.py`、`nextbot/plugins/warehouse.py`、`nextbot/plugins/tutorial.py`、`nextbot/plugins/tutorial_data.py`、`server/pages/{warehouse,red_packet_own,red_packet_all,tutorial}_page.py`、`server/templates/{warehouse,red_packet_own,red_packet_all,tutorial}.html`、`server/routes/webui_warehouse.py`、`server/webui/templates/warehouse_content.html`、`server/webui/static/js/warehouse.js`
- 修改：`nextbot/db.py`（WarehouseItem + value + ensure_warehouse_schema + guest seed 加 6 项 warehouse 权限）、`nextbot/plugins/{economy,user_manager,ban,server_manager,server_send,permission_manager,group_manager,group_member_notify,server_tools,red_packet,player_query,menu}.py`（统一 reply 模板）、`bot.py`、`nextbot/text_utils.py`（新增 EMOJI_GUIDE/EMOJI_WAREHOUSE）、`server/{web_server,routes/{render,webui},pages/console_page}.py`、`server/webui/{templates/app_shell_base,static/js/users}.html/js`


### Git Commits

| Hash | Message |
|------|---------|
| `eaa93f0` | (see git log) |
| `bae3905` | (see git log) |
| `2357809` | (see git log) |
| `935f18c` | (see git log) |
| `411c408` | (see git log) |
| `0eb3e36` | (see git log) |
| `459bb75` | (see git log) |
| `57b6a99` | (see git log) |
| `ab05ca1` | (see git log) |
| `d903106` | (see git log) |
| `82542f3` | (see git log) |
| `09f6abc` | (see git log) |
| `d25e17b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 61: 新增「使用教程 仓库系统」并收紧仓库截图高度

**Date**: 2026-04-23
**Task**: 新增「使用教程 仓库系统」并收紧仓库截图高度

### Summary

(Add summary)

### Main Changes

| 模块 | 改动 |
|---|---|
| 仓库截图 | 移除 `min-h-screen`、收紧 body / header / grid padding、cell 比例 3/4 → 4/5、viewport 1800 → 600；图片显著变矮，无下方留白 |
| 使用教程 | 新增「仓库系统」教程（共 7 步），与「新手教程」并列 |

**新教程结构**：
- 第 1 步：什么是仓库（来源：抽奖 / 商店；容量 100；进度门槛概念）
- 第 2 步：查看仓库（我的仓库 / 用户仓库，只放 user 气泡，desc + tip 说明会出图）
- 第 3 步：看懂仓库截图（卡片元素逐项解释 + 进度颜色阶段）
- 第 4 步：格子表达式（5 种写法 + 多格不支持数量参数的提醒）
- 第 5 步：领取仓库物品（5 个示例覆盖单格 / 数量 / 区间 / 列表 / 全部 + 成功 + 进度不足失败示例）
- 第 6 步：回收仓库物品（公式 + 5 个示例 + 真实成功回复）
- 第 7 步：丢弃仓库物品（5 个示例 + 真实成功回复）

**对齐源码的关键点**：
- 成功回复字段顺序与 emoji 经源码逐行核对（领取：🎁→🖥️→👤→📦→📊；回收：🎁→📦→💰单价→📊比例→💰获得→💰当前→📊；丢弃：🎁→📦→📊）
- 失败回复格式 `@你 ❌ XX失败，原因` 单行
- 沿用「@你」pronoun 风格（与新手教程一致）
- 跳过管理员独占的添加 / 删除命令

**Updated Files**:
- `nextbot/plugins/warehouse.py`（截图 viewport 调小）
- `server/templates/warehouse.html`（移除 min-h-screen + padding 收紧 + cell 比例调整）
- `nextbot/plugins/tutorial_data.py`（追加 `"仓库系统"` 教程项，7 step）

**用户反馈**：
- 第一轮：图片太高 → 改 cell 比例 + 收紧 padding
- 第二轮：水印下面还有空白 → 改 viewport_height 1800 → 600
- 第三轮：第 5/6/7 步示例太单一 → 每步扩到 5 个示例（覆盖单格 / +数量 / 区间 / 列表 / 全部）


### Git Commits

| Hash | Message |
|------|---------|
| `0955d45` | (see git log) |
| `6d11b04` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
