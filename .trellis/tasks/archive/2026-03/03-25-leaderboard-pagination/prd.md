# 排行榜翻页功能

## Goal

为金币排行榜和连续签到排行榜新增翻页支持。

## 命令变化

```
金币排行榜 [页数]
连续签到排行榜 [页数]
```

- 页数为可选，默认第 1 页
- 页数非正整数 → 提示"页数必须为正整数"
- 页数超出范围 → 提示"超出总页数（共 X 页）"

## 数据逻辑

- 每页条数由 `limit` 参数控制（默认 10）
- `offset = (page - 1) * limit`
- 需查询总用户数以计算 `total_pages = ceil(total_count / limit)`
- 查询时加 `.offset(offset).limit(limit)`

## UI 变化

- `leaderboard_page.build_payload` 新增 `page: int`、`total_pages: int` 字段
- 页脚显示"第 X 页 / 共 Y 页"
- **仅第 1 页**显示颁奖台大卡片（`page === 1`），其余页全部走列表样式

## Files to Modify

- `nextbot/plugins/leaderboard.py`
- `server/pages/leaderboard_page.py`
- `server/templates/leaderboard.html`
