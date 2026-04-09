# NextBot Windows 安装教程（小白向）

本教程面向完全没有接触过 NextBot 的新手，按顺序一步一步做即可。建议全程在你准备作为机器人运行环境的 Windows 机器（家用电脑或云服务器皆可）上操作。

---

## 0. 你需要准备什么

- 一台 Windows 机器（x64 或 arm64 架构）
- 一台已经在运行的 **TShock 泰拉瑞亚服务器**（可以在同一台机子上，也可以在另一台机子上）
- 一个将用作机器人的 **QQ 账号**（建议新号，和你的大号区分）
- 一个 QQ 群，用于接收和发送命令
- 能访问 GitHub 的网络环境

---

## 1. 给 TShock 安装 NextBotAdapter 插件

NextBotAdapter 是 NextBot 的**服务端适配插件**，必须安装，否则 NextBot 无法与 TShock 通信。

1. 打开 Release 页面：<https://github.com/Arispex/NextBotAdapter/releases/>
2. 下载**最新版本**的 `NextBotAdapter.dll`
3. 把 `NextBotAdapter.dll` 放入 TShock 的 `ServerPlugins/` 目录
4. 重启 TShock 服务器

> 重启后服务端控制台如果提示 “连接 NextBot 失败” 之类的信息**不用管**，后面配置完 NextBot 就会自动恢复。

---

## 2. 安装 QQ 和运行库（在运行 NextBot 的那台 Windows 上）

1. 下载并安装 [腾讯 QQ](https://im.qq.com/)。**安装完成后不要打开它**，NextBot 配套的 NapCat 会替你登录这个 QQ。
2. 下载并安装微软常用运行库：
   <https://github.com/Arispex/nextbot/releases/download/%E5%BE%AE%E8%BD%AF%E5%B8%B8%E7%94%A8%E8%BF%90%E8%A1%8C%E5%BA%93/default.exe>
   一路下一步即可，这一步能避免后续运行时缺 DLL 报错。

---

## 3. 下载 NextBot 安装器

1. 打开 Release 页面：<https://github.com/Arispex/NextBotInstaller/releases>
2. 根据你的系统架构下载对应文件：
   - **x64 架构**（绝大多数 Windows 电脑）→ `NextBotInstaller-win-x64.zip`
   - **arm64 架构**（如部分 Windows on ARM 设备） → `NextBotInstaller-win-arm64.zip`
   - 不确定架构？直接选 **x64**。
3. 解压压缩包，会得到一个 **`NextBot` 文件夹**。
4. 把整个 `NextBot` 文件夹放到你希望的位置，例如桌面。

> ⚠️ **重要**：安装器会把所有安装文件直接放到它自身所在的目录。如果你把 `NextBotInstaller.exe` 单独拖到桌面运行，桌面就会瞬间多出一大堆文件（类似把一个游戏直接装进桌面），非常难清理。请务必保持它在 `NextBot` 文件夹**内**运行。

---

## 4. 用安装器安装 NextBot 和 NapCat

双击 `NextBot` 文件夹内的 `NextBotInstaller.exe`，会出现一个命令行菜单。

### 4.1 安装 NextBot 本体

1. 用方向键选择「安装 NextBot」，回车
2. 用方向键选择「稳定版（最新 Release）」，回车
3. 等待下载安装完成

### 4.2 安装 NapCat

NapCat 是用来让 QQ 账号被程序控制的组件。

1. 在安装器菜单中用方向键选择「安装 NapCat」，回车
2. 用方向键选择「NapCat.Shell」，回车
3. 等待安装完成

安装完成后，`NextBot` 文件夹根目录会多出两个启动脚本：

| 脚本 | 作用 |
|---|---|
| `run_napcat.bat` | 启动 NapCat（负责登录机器人 QQ） |
| `run_bot.bat` | 启动 NextBot 本体 |

---

## 5. 启动 NapCat 并登录机器人 QQ

双击 `run_napcat.bat`，会弹出一个黑色命令行窗口。

**在窗口里往上翻**，找到类似下面这两行：

```
04-09 11:21:32 [info] [NapCat] [WebUi] WebUi Token: 9f9ff33649d4
04-09 11:21:32 [info] [NapCat] [WebUi] WebUi User Panel Url: http://127.0.0.1:6099/webui?token=9f9ff33649d4
```

其中：

- `http://127.0.0.1:6099/webui?token=9f9ff33649d4` 是 **NapCat WebUI 地址**
- `9f9ff33649d4` 是 **NapCat WebUI 登录 Token**

> 📌 这个 Token 是固定的，不会每次启动都变化。上面示例里的 `9f9ff33649d4` 只是举例，请以你自己窗口里显示的为准。

### 5.1 打开 NapCat WebUI 登录 QQ

1. 在**这台运行 NapCat 的机器的浏览器**里打开上面那个 URL
   - 如果是云服务器，就用云服务器自带的远程桌面/浏览器打开；不能直接用你本地电脑打开 `127.0.0.1`。
2. 如果提示输入 Token，就把上面的 `9f9ff33649d4` 填进去
3. 登录你准备作为机器人的 QQ 账号，**推荐扫码登录**

### 5.2 配置 NapCat 的 WebSocket 服务

1. 登录后，点击左侧导航栏的 **网络配置**
2. 点击 **新建**，类型选择 **WebSocket 服务器**
3. 勾选 **启用**
4. **名称** 随便填一个，比如 `nextbot`
5. **Host**（监听地址）：
   - NapCat 和 NextBot 在**同一台机子** → 保持默认（本地 `127.0.0.1`）即可
   - NapCat 和 NextBot 在**不同机子** → 填 `0.0.0.0`（监听公网）
6. **端口**：随便填一个没被占用的端口，比如 `3001`，**记下来**
7. **Token**：随便填一串，比如 `mynapcattoken`，**记下来**
8. 保存

> 📌 把 **端口** 和 **Token** 记住，后面配置 NextBot 时要用。

---

## 6. 启动 NextBot

双击 `run_bot.bat`，会再弹出一个命令行窗口。运行后可以看到类似的日志：

```
04-09 13:27:32 [INFO] server | Web Server 已启动：http://0.0.0.0:18081
04-09 13:27:32 [INFO] server | Web UI：http://127.0.0.1:18081/webui
04-09 13:27:32 [INFO] server | 已初始化 Web UI 认证文件：C:\Users\Administrator\Desktop\NextBot\.webui_auth.json
04-09 13:27:32 [WARNING] server | Web UI Token：gnQed0wfQ6pDRGlbjONpkV7cTVk-5_gd
```

其中：

- `http://127.0.0.1:18081/webui` 是 **NextBot 的 WebUI 地址**
- `gnQed0wfQ6pDRGlbjONpkV7cTVk-5_gd` 是 **NextBot WebUI 登录 Token**

> 📌 把这个 Token 也记下来，后面登录 WebUI 会用到。它保存在 `.webui_auth.json` 里，不会每次启动都变。

---

## 7. 配置 NextBot（在 WebUI 里操作）

在那台机器的浏览器中打开 `http://127.0.0.1:18081/webui`，用上面的 Token 登录。

### 7.1 填写 OneBot 和管理员配置

1. 点击左侧导航栏的 **设置**
2. 找到并填写以下四项：

| 字段 | 说明 |
|---|---|
| **OneBot WebSocket 地址（逗号分隔）** | NapCat 监听的地址。例如同机 + 端口 3001 就填 `ws://127.0.0.1:3001`；不同机则把 `127.0.0.1` 换成 NapCat 所在机子的公网 IP |
| **OneBot 访问令牌** | 第 5.2 步在 NapCat 里记下的 Token |
| **管理员 QQ（逗号分隔）** | 拥有最高权限的 QQ 号，通常填你自己大号。多个用英文逗号分隔 |
| **允许群号（逗号分隔）** | 机器人只会在这几个群里收发消息，其它群一律忽略 |

3. 点击右上角 **保存并重启**
4. 等待约 5 秒，点击左侧 **仪表盘**
5. 仪表盘上的 **Bot 连接概览** 如果显示出了机器人 QQ 号，说明前面两项 OneBot 配置正确；否则回去检查地址、端口、Token 是否填错

### 7.2 添加 TShock 服务器

1. 点击左侧导航栏的 **服务器管理**
2. 点击 **添加**，填入你的 TShock 服务器信息（IP、端口、Token 等）
3. 保存后点击该行的 **测试** 按钮
4. 如果提示连接失败，回去检查 IP / 端口 / Token；成功后继续下一步

### 7.3 配置服务端插件（NextBotAdapter）

1. 在服务器列表中，点击该行的 **插件配置** 按钮
2. **必须修改** 以下两项：

| 字段 | 填什么 |
|---|---|
| **NextBot 服务地址** | NextBot WebUI 运行的地址。例如同机就是 `http://127.0.0.1:18081`；不同机就把 IP 换成 NextBot 所在机子的公网 IP |
| **NextBot Token** | 第 6 步 NextBot 控制台里打印的 WebUI Token，例如 `gnQed0wfQ6pDRGlbjONpkV7cTVk-5_gd` |

3. 填完后点击下方的 **验证连通性** 按钮
   - 点击后会先自动保存这两项，再触发服务端 → NextBot 的连通性检测
   - 成功 → 说明 TShock 端的 NextBotAdapter 已经能正常连回 NextBot
   - 失败 → 检查地址、端口是否正确，以及防火墙/安全组是否放行
4. 其他字段按自己需求调整，完成后点 **保存**

---

## 8. 测试机器人

在你 **允许群号** 里配置过的 QQ 群内发送消息：

```
菜单
```

如果机器人回复了命令菜单图片，说明部署全部成功 🎉

---

## 常见问题

**Q：仪表盘上 Bot 连接概览一直不显示 QQ？**
A：九成是 OneBot WebSocket 地址或访问令牌填错了。确认 NapCat 网络配置里的 WebSocket 服务是**启用**状态，端口、Token 和 NextBot 里填的完全一致。

**Q：验证连通性 按钮一直失败？**
A：确认 NextBot 服务地址填的是**NextBotAdapter 所在机器**能访问到的地址。如果是跨机部署，不要填 `127.0.0.1`，要填 NextBot 那台机器的公网 IP，并确保防火墙放行 18081 端口。

**Q：群里发 `菜单` 没反应？**
A：检查这个群号是否在 **允许群号** 列表中；检查发送人是否被机器人屏蔽/权限不足；查看 NextBot 命令行窗口是否有报错日志。

---

## 附录：云服务器远程访问说明

如果你把 NextBot / NapCat 装在**云服务器**上，并且希望从自己的电脑浏览器远程打开它们的 WebUI，需要额外做两件事：

1. **放行对应端口**：在云服务商控制台的 **安全组 / 防火墙** 规则里，放行下列端口的入站 TCP：

   | 端口 | 用途 |
   |---|---|
   | `6099` | NapCat WebUI |
   | `18081` | NextBot WebUI |
   | NapCat WebSocket 端口（如 `3001`） | 仅当 NapCat 和 NextBot **不在同一台机子** 时才需要放行 |

   同时确认 Windows 自带的防火墙也放行了这几个端口。

2. **用公网 IP 访问**：不要再用 `127.0.0.1`，而是把地址里的 IP 换成云服务器的**公网 IP**，例如：

   - NapCat WebUI → `http://<公网IP>:6099/webui?token=<你的Token>`
   - NextBot WebUI → `http://<公网IP>:18081/webui`

> ⚠️ 两个 WebUI 的 Token 就是登录凭据，**不要把带 Token 的 URL 发给别人**。
