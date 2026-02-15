<h1 align="center">
next-bot
<br>
<h4 align="center">
一个基于 <a href="https://nonebot.dev/">NoneBot2</a> 的 Terraria <a href="https://github.com/Pryaxis/TShock">TShock</a> QQ 机器人
</h4>
</h1>

## 声明
本项目仅用于学习与技术交流，请勿用于非法用途。

## 关于本项目
`next-bot` 是一个基于 <a href="https://nonebot.dev/">NoneBot2</a> 的 Terraria <a href="https://github.com/Pryaxis/TShock">TShock</a> QQ 机器人

## 快速开始
1. 安装依赖（推荐使用 `uv`）
```bash
uv sync
```

2. 配置环境变量（`.env`）
```env
# NoneBot
LOG_LEVEL=INFO
DRIVER=~websockets
LOCALSTORE_USE_CWD=true
COMMAND_START=["/", ""]

# 访问控制（仅允许这些私聊/群消息）
OWNER_ID=["123456789","987654321"]
GROUP_ID=["123456789"]

# OneBot V11 反向 WS
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
ONEBOT_ACCESS_TOKEN=your_token

# 渲染服务（用户背包/世界进度截图）
RENDER_SERVER_HOST=127.0.0.1
RENDER_SERVER_PORT=18081
RENDER_SERVER_PUBLIC_BASE_URL=http://127.0.0.1:18081

# 代理功能（可选）
LLM_API_KEY=your_api_key
LLM_MODEL=your_model
LLM_BASE_URL=https://your-api-endpoint/v1/chat/completions
```

3. 启动机器人
```bash
uv run python bot.py 
```

## 关于许可证
本项目基于 AGPL v3.0 许可证授权发行，您可以在遵守许可证的前提下自由使用、复制、修改、发布和分发本项目。

有关 AGPL v3.0 许可证的详细信息，请参阅 https://www.gnu.org/licenses/agpl-3.0.html
