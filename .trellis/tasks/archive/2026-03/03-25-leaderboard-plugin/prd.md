# 排行榜插件

## Goal

新建 `leaderboard.py` 插件，首个功能为金币排行榜，以网页渲染截图的方式发送图片。

## 命令

```
金币排行
```

## 数据来源

查询 `User` 表，按 `coins` 降序排列，取前 N 名（可配置，默认 10）。

展示字段：排名、用户名称、金币数。

## 渲染方式

与现有插件一致：
1. 新建 `server/pages/leaderboard_page.py`（build_payload + render）
2. 新建 `server/templates/leaderboard.html`（排行榜样式，高大上）
3. `server/web_server.py` 新增 `create_leaderboard_page`
4. `server/routes/render.py` 注册 `/render/leaderboard/{token}` 路由

## 样式方向

- 暗色主题（与进度页风格保持一致）
- 每一行：排名徽章（金/银/铜 + 数字）、用户名、金币数
- 顶部标题 + 生成时间

## command_control 参数

```python
command_key="leaderboard.coins"
display_name="金币排行"
permission="leaderboard.coins"
params:
  limit: int, default=10, min=1, max=50, label="显示名次"
```

## Files to Create/Modify

- `nextbot/plugins/leaderboard.py`（新建）
- `server/pages/leaderboard_page.py`（新建）
- `server/templates/leaderboard.html`（新建）
- `server/web_server.py`（新增 create_leaderboard_page）
- `server/routes/render.py`（新增路由）
