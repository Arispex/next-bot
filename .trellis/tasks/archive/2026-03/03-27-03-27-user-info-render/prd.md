# 用户信息图片渲染

## Goal

将「我的信息」和「用户信息」命令改为网页截图方式输出，支持双主题，展示用户基本信息 + 签到贡献墙。

## 页面设计

### 布局（从上至下）

**Header**
- 左：QQ 头像（圆形，100×100，从 `http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100` 加载）
- 右：用户名（大字）、用户 ID（次级）、身份组 badge、注册时间

**Stats 卡片行**（横排 4 格）
- 金币
- 累计签到
- 连续签到
- 权限（逗号分隔 badge 列表，若无则显示「无」）

**签到贡献墙**
- 类似 GitHub contribution graph：最近 N 天（默认 90，可配置），每天一格
- 从左到右按周列排列（7 行 × 列数），最新一天在右下角
- 已签到：绿色（亮色）/ indigo（暗色）；未签到：浅灰格
- 上方显示月份标签

### 双主题
- 亮色：白色卡片、浅蓝灰背景，绿色贡献墙
- 暗色：深色石砖背景、暗色玻璃卡片，indigo/blue 贡献墙

## 数据来源

- 用户基本信息：本地 `User` 表（user_id, name, coins, sign_streak, sign_total, permissions, group, created_at）
- 签到历史：`UserSignRecord` 表，按 user_id 查询最近 N 天日期
- QQ 头像：HTML `<img>` 直接引用外部 URL，截图时 Playwright 会加载

## 命令参数变更

- `command_control` 新增 `days` 参数：贡献墙天数，默认 90，范围 7-365

## Files to Modify / Create

- `server/pages/user_info_page.py`（新建）：build_payload / render
- `server/templates/user_info.html`（新建）：渲染模板
- `server/web_server.py`：新增 `create_user_info_page`
- `server/routes/render.py`：新增 `/render/user_info/{token}` 路由（参考其他）
- `nextbot/plugins/user_manager.py`：`handle_user_info` / `handle_self_info` 改为截图方式

## Acceptance Criteria

- [ ] `我的信息` / `用户信息` 输出截图
- [ ] 页面包含头像、用户名、stats、贡献墙
- [ ] 亮色/暗色主题均正常渲染
- [ ] 贡献墙正确高亮已签到日期
- [ ] `days` 参数可调整贡献墙范围
