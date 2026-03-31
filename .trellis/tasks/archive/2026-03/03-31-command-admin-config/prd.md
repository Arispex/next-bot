# 命令管理菜单显示配置

## Goal

目前每个命令的 `admin` 字段（控制是否显示在管理菜单）是在 `@command_control(admin=True/False)` 中硬编码的。
希望将其改为可配置：有一个来自代码的默认值，用户可以在 WebUI 上自行修改每个命令的 `admin` 设置。

## Current State

- `admin` 仅存在于 `RegisteredCommand`（内存注册表），不存在于 `CommandConfig` 数据库表
- `_to_runtime_state()` 中通过 `registered.admin` 读取，始终以代码中的硬编码值为准
- `update_command_config()` 不支持修改 `admin`
- WebUI 命令管理页面不展示 `admin` 字段

## Requirements

### 后端

1. **DB 迁移**：在 `command_config` 表新增 `admin` 列（`BOOLEAN NOT NULL DEFAULT 0`）
2. **`ensure_command_config_schema()`**：补充 `admin` 列的 ALTER TABLE 迁移
3. **`sync_registered_commands_to_db()`**：
   - 新增行时：用 `registered.admin` 作为初始值写入 `admin` 列
   - 已有行时：**不覆盖** 用户的设置（保持 DB 中已有值），除非该行是新创建的
4. **`_to_runtime_state()`**：`admin` 从 `row.admin`（DB 列）读取，不再从 `registered.admin` 读取
5. **`update_command_config()`**：新增 `admin` 可选参数，支持修改
6. **WebUI API** (`PATCH /webui/api/commands/{command_key}`)：接受 `admin` 字段

### 前端

7. **命令列表页**：在命令卡片/行中展示当前 `admin` 值（标识是否显示在管理菜单）
8. **编辑命令**：在编辑面板中增加 `admin` 开关，可切换并保存

## Acceptance Criteria

- [ ] DB 中存在 `admin` 列，已有数据库通过迁移自动补充（值为 0）
- [ ] 首次同步时，代码中 `admin=True` 的命令在 DB 中 `admin=1`，`admin=False` 的为 0
- [ ] 重启后不覆盖用户在 WebUI 中修改的 `admin` 值
- [ ] WebUI 命令编辑界面可修改 `admin` 字段并保存
- [ ] `list_command_configs()` 返回的 `admin` 字段反映 DB 中的实际值

## Technical Notes

- `CommandConfig` model 新增 `admin: Mapped[bool]`，`mapped_column(Boolean, nullable=False, default=False)`
- `sync_registered_commands_to_db()` 对已有行：只在 `admin` 列不存在时（迁移刚完成、值为默认 0）考虑是否以 `registered.admin` 覆盖；但更简单的做法是：**新行用代码默认值，老行保留 DB 值**——SQLAlchemy 对已有行不会 reset 字段，所以只要不显式赋值就行
- WebUI 前端参考现有 `enabled` 的开关样式
