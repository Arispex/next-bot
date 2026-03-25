# 背包页面图片主题适配

## Goal

为背包截图渲染新增暗色主题，支持 `render_theme` 配置（dark/light/auto）。

## 实现方案

与进度页完全对称：

1. `server/pages/inventory_page.py`：`build_payload` / `render` 新增 `theme: str` 参数
2. `server/web_server.py`：`create_inventory_page` 新增 `theme: str` 参数
3. `nextbot/plugins/basic.py`：两处 `create_inventory_page` 调用传入 `resolve_render_theme()`
4. `server/templates/inventory.html`：`[data-theme]` 双主题实现

## 主题设计

**亮色（现有）**：蓝色渐变 header、白色分区卡片、浅蓝物品格

**暗色（新增）**：
- 背景：`#0d0d0f`（与进度页暗色同系）
- Header：深蓝紫渐变
- 分区卡片：深色玻璃感，蓝紫边框
- 物品格：有物品时深色 + 微发光蓝边，空格极暗
- 统计栏、tooltip 等均适配

## Files to Modify

- `server/pages/inventory_page.py`
- `server/web_server.py`
- `nextbot/plugins/basic.py`
- `server/templates/inventory.html`
