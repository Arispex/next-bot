# 排行榜图片主题适配

## Goal

让金币排行榜和连续签到排行榜支持 `render_theme` 配置（dark/light/auto），编写亮色主题。

## auto 判断逻辑

- 北京时间 06:00–20:00 → `light`
- 其余时段 → `dark`

## 实现方案

### 1. 主题解析工具函数（`nextbot/plugins/leaderboard.py`）

```python
def _resolve_theme() -> str:
    from nonebot import get_driver
    theme = str(getattr(get_driver().config, "render_theme", "auto")).strip().lower()
    if theme == "auto":
        hour = beijing_now().hour
        return "light" if 6 <= hour < 20 else "dark"
    return theme if theme in {"dark", "light"} else "dark"
```

### 2. 传递 theme 字段

- `leaderboard_page.build_payload` 新增 `theme: str` 参数
- `web_server.create_leaderboard_page` 新增 `theme: str` 参数
- plugin 调用时传入 `_resolve_theme()`

### 3. HTML 双主题

`leaderboard.html` 根据 `data.theme` 切换 CSS 变量或 class，实现暗色/亮色两套样式：

**暗色**（现有）：深黑背景、暗色卡片、金/银/铜发光

**亮色**（新增）：
- 背景：`linear-gradient(160deg, #f0f4ff, #f8fafc, #eef2f7)`
- 颁奖台卡片：白色底、淡金/银/铜边框
- 排名数字：深色，无 glow
- 列表行：白色/极浅灰，细边框
- 整体与背包页亮色主题保持同系风格

## Files to Modify

- `nextbot/plugins/leaderboard.py`
- `server/pages/leaderboard_page.py`
- `server/web_server.py`
- `server/templates/leaderboard.html`
