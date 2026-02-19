from __future__ import annotations

import html


def render_login_page(*, next_path: str, error_message: str = "") -> str:
    escaped_next = html.escape(next_path, quote=True)
    escaped_error = html.escape(error_message)

    error_html = ""
    if escaped_error:
        error_html = (
            '<p class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 '
            'text-sm text-red-700">'
            f"{escaped_error}"
            "</p>"
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NextBot WebUI Login</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            primary: {{
              50: "#eff6ff",
              100: "#dbeafe",
              500: "#3b82f6",
              600: "#2563eb",
              700: "#1d4ed8"
            }}
          }}
        }}
      }}
    }};
  </script>
</head>
<body class="min-h-screen bg-gradient-to-br from-primary-100 via-slate-50 to-primary-50 p-4 text-slate-900">
  <main class="mx-auto mt-20 w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl">
    <section class="border-b border-slate-100 px-6 py-5">
      <p class="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-1 text-xs font-semibold text-primary-700">
        NextBot WebUI
      </p>
      <h1 class="mt-3 text-2xl font-semibold">控制台登录</h1>
      <p class="mt-2 text-sm text-slate-500">请输入访问 Token 以进入控制台。</p>
    </section>
    <section class="px-6 py-5">
      {error_html}
      <form method="post" action="/webui/login" class="space-y-4">
        <input type="hidden" name="next" value="{escaped_next}" />
        <div>
          <label for="token" class="mb-1 block text-sm font-medium text-slate-700">Token</label>
          <input
            id="token"
            name="token"
            type="password"
            autocomplete="off"
            placeholder="请输入 WEBUI_TOKEN"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-primary-300 transition focus:border-primary-500 focus:ring-2"
          />
        </div>
        <button
          type="submit"
          class="inline-flex w-full items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
        >
          登录控制台
        </button>
      </form>
    </section>
  </main>
</body>
</html>
"""


def render_console_page() -> str:
    module_cards = [
        ("Server Management", "服务器管理能力（占位）"),
        ("User Management", "用户管理能力（占位）"),
        ("Group & Permission", "身份组与权限能力（占位）"),
        ("Agent Console", "代理控制能力（占位）"),
        ("Render Center", "渲染中心能力（占位）"),
    ]
    cards_html = "".join(
        [
            (
                '<article class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">'
                f'<h2 class="text-base font-semibold text-slate-900">{title}</h2>'
                f'<p class="mt-2 text-sm text-slate-500">{desc}</p>'
                "</article>"
            )
            for title, desc in module_cards
        ]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NextBot WebUI</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            primary: {{
              50: "#eff6ff",
              100: "#dbeafe",
              500: "#3b82f6",
              600: "#2563eb",
              700: "#1d4ed8"
            }}
          }}
        }}
      }}
    }};
  </script>
</head>
<body class="min-h-screen bg-gradient-to-br from-primary-100 via-slate-50 to-primary-50 p-5 text-slate-900">
  <main class="mx-auto max-w-6xl rounded-2xl border border-slate-200 bg-white shadow-xl">
    <header class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 px-6 py-5">
      <div>
        <p class="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-1 text-xs font-semibold text-primary-700">
          NextBot WebUI
        </p>
        <h1 class="mt-2 text-2xl font-semibold text-slate-900">控制台（骨架）</h1>
      </div>
      <div class="flex gap-2 text-xs">
        <span class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 font-semibold text-emerald-700">status: running</span>
        <span class="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 font-semibold text-slate-600">version: v0</span>
      </div>
    </header>

    <section class="px-6 py-5">
      <p class="mb-4 text-sm text-slate-500">当前页面仅为控制台占位骨架，后续功能将逐步接入。</p>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards_html}
      </div>
    </section>
  </main>
</body>
</html>
"""
