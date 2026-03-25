# 菜单功能拆分与样式优化

## Goal

将「菜单」拆分为「菜单」（普通用户）和「管理菜单」（管理员），同时完全重设计渲染页面样式。

## 命令拆分逻辑

**管理命令前缀**（显示在管理菜单）：
- `group.`
- `permission.`
- `server.`
- `user.coins.`

**普通菜单**（`菜单`命令）：所有不属于管理前缀的命令
**管理菜单**（`管理菜单`命令）：所有属于管理前缀的命令

## 涉及文件

### `nextbot/plugins/menu.py`
- 新增 `admin_menu_matcher = on_command("管理菜单")`
- `handle_menu`：过滤掉管理命令
- `handle_admin_menu`：只显示管理命令
- 两个 handler 都通过 `title` 区分传给 `create_menu_page`

### `server/pages/menu_page.py`
- `build_payload` 新增 `title: str` 参数
- `render` 将 `title` 传入模板 JSON

### `server/web_server.py`
- `create_menu_page` 新增 `title: str` 参数，传给 `menu_page.build_payload`

### `server/templates/menu.html`
- 完全重设计：卡片式网格布局，替换现有表格
- 每张卡片：命令名称（大号）、介绍、用法（等宽代码样式）、权限徽章
- 标题从 `data.title` 读取
- 现代简洁高级感，3 列网格，截图友好（1920px 宽）

## Acceptance Criteria

- [ ] `菜单` 只显示普通命令（不含 group/permission/server/user.coins 前缀）
- [ ] `管理菜单` 只显示管理命令
- [ ] 两个命令都能正常截图发送
- [ ] 页面标题正确区分
- [ ] 新样式卡片式布局，视觉效果高级
