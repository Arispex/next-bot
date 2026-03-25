# 进度页面图片主题适配

## Goal

为世界进度截图渲染新增亮色主题，支持 `render_theme` 配置（dark/light/auto）。

## 实现方案

与排行榜主题适配完全对称：

1. `server/pages/progress_page.py`：`build_payload` / `render` 新增 `theme: str` 参数
2. `server/web_server.py`：`create_progress_page` 新增 `theme: str` 参数
3. `nextbot/plugins/basic.py`：`handle_world_progress` 调用 `_resolve_theme()`（已在 leaderboard 中定义，需复用或提取到公共位置）
4. `server/templates/progress.html`：`[data-theme]` 双主题实现

## 主题设计

**暗色（现有）**：Terraria 石砖风格，深黑背景，金色标题，金/绿高亮

**亮色（新增）**：
- 背景：`linear-gradient(160deg, #f0f4ff, #f8fafc, #eef2f7)`（与背包页同系）
- 进度容器：白色圆角卡片，浅色边框
- 已击败卡片：淡绿/淡蓝高亮
- 未击败卡片：浅灰
- 标题、文字：深色系

## `_resolve_theme` 复用方案

从 `leaderboard.py` 提取到公共模块，或直接在 `basic.py` 中内联一份相同的函数（后者更简单，当前只有两处使用）。

## Files to Modify

- `server/pages/progress_page.py`
- `server/web_server.py`
- `nextbot/plugins/basic.py`
- `server/templates/progress.html`
