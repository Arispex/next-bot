from __future__ import annotations

from typing import Any

TUTORIALS: dict[str, dict[str, Any]] = {
    "新手教程": {
        "slug": "新手教程",
        "title": "新手教程",
        "subtitle": "从零开始加入服务器",
        "emoji": "🌱",
        "steps": [
            {
                "title": "第 1 步：注册账号",
                "desc": "在群里发送「注册账号 你的名字」，机器人会在所有服务器为你创建角色。\n\n⚠️ 这里的「你的名字」必须与你游戏内使用的角色名称完全一致，否则无法加入服务器。",
                "chat": [
                    {"role": "user", "name": "你", "avatar": "__SELF__", "text": "注册账号 小明"},
                    {"role": "bot", "name": "NextBot", "avatar": "__BOT__",
                     "text": "@你\n✅ 注册成功\n👤 用户名称：小明\n🆔 QQ：123456"},
                ],
                "tip": {"type": "hint", "text": "名字里不要有空格和特殊符号，不能纯数字，太长也不推荐。"},
            },
            {
                "title": "第 2 步：选择要进的服务器",
                "desc": "发送「服务器列表」或查看群公告，找到想进的服务器，记下 IP 和端口。",
                "chat": [
                    {"role": "user", "name": "你", "avatar": "__SELF__", "text": "服务器列表"},
                    {"role": "bot", "name": "NextBot", "avatar": "__BOT__",
                     "text": "🖥️ 服务器列表\n1.生存服\nIP：123.45.67.89\n端口：7777\n\n2.模组服\nIP：123.45.67.89\n端口：7778"},
                ],
                "tip": None,
            },
            {
                "title": "第 3 步：打开游戏加入服务器",
                "desc": "移动端 / 手机版：\n打开游戏 → 多人游戏 → 选择一个角色（⚠️ 角色名称务必与第 1 步注册时填写的完全一致）→ 点击右下方的「连接」→ 输入「IP 地址」和「端口」后点击「加入」。",
                "chat": None,
                "tip": {"type": "warn", "text": "如果游戏提示「不在白名单内」，先回群里继续第 4 步。"},
            },
            {
                "title": "第 4 步：同步白名单（仅在提示白名单错误时执行）",
                "desc": "仅在第 3 步尝试加入服务器时，游戏提示「不在白名单内」才需要执行。\n\n发送「同步白名单」，机器人会把你加入所有服务器的白名单。",
                "chat": [
                    {"role": "user", "name": "你", "avatar": "__SELF__", "text": "同步白名单"},
                    {"role": "bot", "name": "NextBot", "avatar": "__BOT__",
                     "text": "@你\n✅ 同步白名单成功\n1.生存服：✅ 同步成功\n2.模组服：✅ 同步成功"},
                ],
                "tip": None,
            },
            {
                "title": "第 5 步：二次验证（首次登入新设备时）",
                "desc": "首次在新设备登入时，机器人会在群里 @你 提示登入请求，发送「允许登入」确认；如果不是你本人尝试登入，发送「拒绝登入」。",
                "chat": [
                    {"role": "bot", "name": "NextBot", "avatar": "__BOT__",
                     "text": "@你\n有新设备正在尝试登入服务器\n请回复「允许登入」或「拒绝登入」\n该请求 5 分钟内有效"},
                    {"role": "user", "name": "你", "avatar": "__SELF__", "text": "允许登入"},
                    {"role": "bot", "name": "NextBot", "avatar": "__BOT__",
                     "text": "@你 ✅ 允许成功，可在 5 分钟内重新连接"},
                ],
                "tip": None,
            },
            {
                "title": "第 6 步：再次加入服务器",
                "desc": "重复第 3 步的加入流程，这次就能顺利进入游戏了！",
                "chat": None,
                "tip": None,
            },
            {
                "title": "第 7 步：探索更多功能",
                "desc": "到这里新手流程就走完啦，欢迎加入！机器人还内置了签到赚金币、红包、抢劫、小游戏、排行榜等丰富功能，随时发「菜单」探索全部可用命令。",
                "chat": None,
                "tip": None,
            },
        ],
    },
}


def list_tutorials() -> list[dict[str, Any]]:
    return list(TUTORIALS.values())


def get_tutorial(slug: str) -> dict[str, Any] | None:
    return TUTORIALS.get(slug)
