# 菜单页面图片主题适配

## Goal

为菜单和管理菜单截图渲染新增暗色主题，支持 render_theme 配置。

## 实现方案（与背包/进度完全对称）

1. `server/pages/menu_page.py`：build_payload / render 新增 theme 参数
2. `server/web_server.py`：create_menu_page 新增 theme 参数
3. `nextbot/plugins/menu.py`：_render_and_send 和两处 create_menu_page 调用传入 resolve_render_theme()
4. `server/templates/menu.html`：[data-theme] 双主题实现

## 暗色主题设计

**亮色（现有）**：白色/浅灰背景，卡片白色底，indigo 权限标签

**暗色（新增）**：
- 背景：深黑石砖纹理（与进度/背包暗色同系）
- 卡片：深色玻璃感，蓝紫边框
- 标题：浅色系
- 序号徽章：深色底，indigo 色调
- usage 块：深色等宽代码风格
- 权限标签：深色 indigo/amber 配色

## Files to Modify

- `server/pages/menu_page.py`
- `server/web_server.py`
- `nextbot/plugins/menu.py`
- `server/templates/menu.html`
