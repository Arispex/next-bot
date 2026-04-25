# NextBot Docker 安装教程（小白向）

本教程面向完全没有接触过 NextBot 的新手，按顺序一步一步做即可。建议全程在你准备作为机器人运行环境的 Linux 服务器（家用机、云服务器或本地 macOS 都可）上操作。

---

## 0. 你需要准备什么

- 一台能装 Docker 的机器（Linux x86_64 / arm64 或 macOS）
- 一台已经在运行的 **TShock 泰拉瑞亚服务器**（可以在同一台机子上，也可以在另一台机子上）
- 一个将用作机器人的 **QQ 账号**（建议新号，和你的大号区分）
- 一个 QQ 群，用于接收和发送命令
- 能访问 GitHub 和 Docker Hub 的网络环境

---

## 1. 给 TShock 安装 NextBotAdapter 插件

NextBotAdapter 是 NextBot 的**服务端适配插件**，必须安装，否则 NextBot 无法与 TShock 通信。

1. 打开 Release 页面：<https://github.com/Arispex/NextBotAdapter/releases/>
2. 下载**最新版本**的 `NextBotAdapter.dll`
3. 把 `NextBotAdapter.dll` 放入 TShock 的 `ServerPlugins/` 目录
4. 重启 TShock 服务器

> 重启后服务端控制台如果提示 "连接 NextBot 失败" 之类的信息**不用管**，后面配置完 NextBot 就会自动恢复。

---

## 2. 安装 Docker（在运行 NextBot 的那台机子上）

### Linux

适用于 Ubuntu / Debian / CentOS / Rocky / Alma 等主流发行版。

> 🇨🇳 **国内网络访问 docker.com 慢或失败？** 先执行下面这行换成清华镜像源，再走下面的安装命令：
>
> ```bash
> export DOWNLOAD_URL="https://mirrors.tuna.tsinghua.edu.cn/docker-ce"
> ```

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

把当前用户加入 `docker` 组，避免每次都要 `sudo`：

```bash
sudo usermod -aG docker $USER
# 重新登录或执行 `newgrp docker` 让权限生效
```

### macOS

下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，启动后等待右上角小鲸鱼图标变绿。

### 验证安装

执行下面两条命令，应该都能输出版本号：

```bash
docker --version
docker compose version
```

> 📌 必须是 `docker compose`（带空格的 v2 写法），而不是老的 `docker-compose`。`get.docker.com` 装出来的就是 v2，没问题。

---

## 3. 创建工作目录并下载 docker-compose.yml

挑一个你方便管理的目录作为机器人根目录，例如 `~/nextbot`：

```bash
mkdir -p ~/nextbot && cd ~/nextbot

curl -fsSL -o docker-compose.yml \
  https://raw.githubusercontent.com/Arispex/nextbot/main/docker-compose.yml
```

`docker-compose.yml` 已经把 NextBot + NapCat（QQ 适配器）配好，下一步直接同时起服。

---

## 4. 一次性启动 NextBot + NapCat

```bash
docker compose up -d
docker compose ps   # 应该看到 nextbot 和 napcat 两个容器都是 Up
```

宿主机当前目录会立刻多出两个文件夹：

| 目录 | 内容 |
|---|---|
| `./data/` | NextBot 状态：`.env`（自动生成默认值）、`app.db`（已建表）、`.webui_auth.json`（含 WebUI 登录 token）|
| `./napcat/` | NapCat 状态：`QQ/` 登录态 + `config/` 配置 + `plugins/` 插件 |

> 📌 NextBot 容器启动后会发现 `.env` 里 `ONEBOT_WS_URLS=[]` 还是空的，控制台会打印 `未配置 ONEBOT_WS_URLS，已跳过 OneBot V11 连接`。这是**预期行为** —— 我们会在第 6 步填好这个配置然后重启它。NapCat 这边不受影响，可以继续下一步。

---

## 5. 在 NapCat WebUI 里登录 QQ 并配置 WebSocket

查看 NapCat 启动日志拿 WebUI 登录 URL：

```bash
docker compose logs napcat | grep -i "webui"
```

会看到类似：

```
[NapCat] [WebUi] WebUi Token: 9f9ff33649d4
[NapCat] [WebUi] WebUi User Panel Url: http://127.0.0.1:6099/webui?token=9f9ff33649d4
```

其中：

- `http://127.0.0.1:6099/webui?token=9f9ff33649d4` 是 **NapCat WebUI 地址**
- `9f9ff33649d4` 是 **NapCat WebUI 登录 Token**

> 📌 这个 Token 是固定的，不会每次启动都变化。上面示例里的 `9f9ff33649d4` 只是举例，请以你自己日志里显示的为准。

### 5.1 打开 WebUI 登录 QQ

1. 在浏览器里打开上面那个 URL
   - **本机部署**：直接打开
   - **云服务器部署**：把 `127.0.0.1` 换成云服务器**公网 IP**，并确保安全组放行 6099 端口（详见文末附录）
2. 如果提示输入 Token，就把上面的 `9f9ff33649d4` 填进去
3. 登录你准备作为机器人的 QQ 账号，**推荐扫码登录**

> 📌 由于 `docker-compose.yml` 把 NapCat 的 QQ 登录态持久化到了 `./napcat/QQ/`，登录一次后即使容器重启或更新镜像，**下次都不需要再扫码**。

### 5.2 配置 NapCat 的 WebSocket 服务

1. 登录后，点击左侧导航栏的 **网络配置**
2. 点击 **新建**，类型选择 **WebSocket 服务器**
3. 勾选 **启用**
4. **名称** 随便填一个，比如 `nextbot`
5. **Host**（监听地址）：填 `0.0.0.0`
   - Docker 容器之间通过虚拟网络通信，必须监听全部网卡，否则容器外的 NextBot 连不进来
6. **端口**：填 `3001`（跟 docker-compose.yml 里 NapCat 暴露的端口一致）
7. **Token**：随便填一串自定义字符串，比如 `mynapcattoken`，**记下来**
8. 保存

> 📌 把 **Token** 记住，下一步配置 NextBot 时要用。

---

## 6. 配置 NextBot（在 WebUI 里操作）

查看 NextBot 启动日志拿 WebUI 登录 Token：

```bash
docker compose logs nextbot | grep "Web UI Token"
```

会看到类似：

```
[WARNING] server | Web UI Token：80FOYqh3OEGqGOgkimKxIZr55N2WxFgQ
```

其中 `80FOYqh3OEGqGOgkimKxIZr55N2WxFgQ` 是 **NextBot WebUI 登录 Token**。

> 📌 这个 Token 保存在 `./data/.webui_auth.json` 里，不会每次启动都变。

在浏览器中打开 NextBot WebUI：

- **本机部署**：<http://127.0.0.1:18081/webui>
- **云服务器部署**：把 `127.0.0.1` 换成云服务器**公网 IP**，并确保安全组放行 18081 端口

用上面的 Token 登录。

### 6.1 填写 OneBot 和管理员配置

1. 点击左侧导航栏的 **设置**
2. 找到并填写以下四项：

| 字段 | 填什么 |
|---|---|
| **OneBot WebSocket 地址（逗号分隔）** | 填 `ws://napcat:3001`（容器之间通过容器名互通，不要改）|
| **OneBot 访问令牌** | 第 5.2 步在 NapCat 里设置的 Token |
| **管理员 QQ（逗号分隔）** | 拥有最高权限的 QQ 号，通常填你自己大号。多个用英文逗号分隔 |
| **允许群号（逗号分隔）** | 机器人只会在这几个群里收发消息，其它群一律忽略 |

3. 点击右上角 **保存并重启**
4. 等待约 5 秒，点击左侧 **仪表盘**
5. 仪表盘上的 **Bot 连接概览** 如果显示出了机器人 QQ 号，说明前面两项 OneBot 配置正确；否则回去检查地址、端口、Token 是否填错

### 6.2 添加 TShock 服务器

1. 点击左侧导航栏的 **服务器管理**
2. 点击 **添加**，填入你的 TShock 服务器信息（IP、端口、Token 等）
3. 保存后点击该行的 **测试** 按钮
4. 如果提示连接失败，回去检查 IP / 端口 / Token；成功后继续下一步

### 6.3 配置服务端插件（NextBotAdapter）

1. 在服务器列表中，点击该行的 **插件配置** 按钮
2. **必须修改** 以下两项：

| 字段 | 填什么 |
|---|---|
| **NextBot 服务地址** | TShock 服务器能访问到 NextBot 的地址。例如同机就是 `http://127.0.0.1:18081`；不同机就把 IP 换成 NextBot 所在机子的公网 IP |
| **NextBot Token** | 第 6 步开头从日志里拿的 WebUI Token |

3. 填完后点击下方的 **验证连通性** 按钮
   - 点击后会先自动保存这两项，再触发服务端 → NextBot 的连通性检测
   - 成功 → 说明 TShock 端的 NextBotAdapter 已经能正常连回 NextBot
   - 失败 → 检查地址、端口是否正确，以及防火墙/安全组是否放行
4. 其他字段按自己需求调整，完成后点 **保存**

---

## 7. 测试机器人

在你 **允许群号** 里配置过的 QQ 群内发送消息：

```
菜单
```

如果机器人回复了命令菜单图片，说明部署全部成功 🎉

---

## 常见运维操作

| 操作 | 命令 |
|---|---|
| 查看实时日志 | `docker compose logs -f nextbot` |
| 重启 NextBot | `docker compose restart nextbot` |
| 升级到最新版本 | `docker compose pull && docker compose up -d` |
| 完全停止 | `docker compose down`（保留持久化数据）|
| 查看容器状态 | `docker compose ps` |

---

## 备份和迁移

整个机器人的状态都在工作目录里：

```
~/nextbot/
├── docker-compose.yml
├── data/                  # NextBot 状态：.env / app.db / .webui_auth.json
└── napcat/                # NapCat 状态
    ├── QQ/                # QQ 登录态（决定下次是否要重新扫码）
    ├── config/            # NapCat 主配置
    └── plugins/           # NapCat 插件
```

**完整备份**：把整个 `~/nextbot/` 目录打包带走即可。

```bash
tar czf nextbot-backup-$(date +%Y%m%d).tar.gz ~/nextbot
```

迁移到新机器：装好 Docker 后，把这个 tar 解压到新机器，`cd` 进去 `docker compose up -d` 即可，**所有登录态、配置和数据库都还在，不需要重新扫码也不需要重新配置**。

---

## 常见问题

**Q：启动后 NextBot 日志一直打 `未配置 ONEBOT_WS_URLS，已跳过 OneBot V11 连接`？**
A：这是第一次启动时的预期行为，因为 `.env` 还是默认值。完成第 6.1 步在 WebUI **设置** 页里填好 OneBot 配置并点 **保存并重启**，就会连上。

**Q：仪表盘 Bot 连接概览一直不显示 QQ？**
A：九成是 **设置** 里 **OneBot WebSocket 地址** 或 **OneBot 访问令牌** 跟 NapCat 配置不一致。注意 NapCat 的 WebSocket 服务必须设为 **启用** 状态，监听 `0.0.0.0:3001`，且 Token 两边完全一致。改完 **设置** 一定要点 **保存并重启**。

**Q：验证连通性 按钮一直失败？**
A：确认 NextBot 服务地址填的是 **NextBotAdapter 所在机器** 能访问到的地址。如果是跨机部署，不要填 `127.0.0.1`，要填 NextBot 那台机器的公网 IP，并确保防火墙放行 18081 端口。

**Q：群里发 `菜单` 没反应？**
A：检查这个群号是否在 **设置** - **允许群号** 列表中；查看 `docker compose logs nextbot` 是否有报错日志。

**Q：NapCat 容器重启后又要扫码？**
A：检查工作目录里 `napcat/QQ/` 文件夹是否存在且非空。`docker-compose.yml` 默认把这个目录挂到容器的 `/app/.config/QQ`，登录态全部持久化在这里。如果误删过这个文件夹就需要重新扫码。

**Q：升级镜像后数据丢了？**
A：理论上不会，所有状态都在挂载的 `./data/` 和 `./napcat/` 里。如果发现数据丢失，请先确认你执行升级时是 `docker compose pull && docker compose up -d` 而不是 `docker compose down -v`（带 `-v` 会删除卷）。

---

## 附录：云服务器端口放行说明

如果你把 NextBot / NapCat 装在**云服务器**上，并且希望从自己的电脑浏览器远程打开它们的 WebUI，需要在云服务商控制台的 **安全组 / 防火墙** 规则里放行下列端口的入站 TCP：

| 端口 | 用途 | 是否必须 |
|---|---|---|
| `6099` | NapCat WebUI（首次登录用） | 是 |
| `18081` | NextBot WebUI | 是 |
| `3001` | NapCat WebSocket | 否（仅当 NapCat 与 NextBot 部署在不同机子时才需要放行） |

> ⚠️ 两个 WebUI 的 Token 就是登录凭据，**不要把带 Token 的 URL 发给别人**。设置完成后 NapCat WebUI 端口可以考虑收回，避免长期暴露。

---

## 附录：自定义部署

如果你不想用 `docker-compose.yml` 自带的 NapCat（例如已有现成的 OneBot 适配器），可以单独跑 NextBot：

```bash
docker run -d \
  --name nextbot \
  --restart unless-stopped \
  -p 18081:18081 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  ghcr.io/arispex/nextbot:latest
```

容器内 `/app/data` 目录用环境变量 `NEXTBOT_DATA_DIR=/app/data` 控制，可以按需改成你喜欢的路径，或挂到 named volume 里。
