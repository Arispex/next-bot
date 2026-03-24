# Directory Structure

> How backend code is organized in this project.

---

## Overview

This project runs the bot runtime and the Web UI runtime in the same repository and process.

- `bot.py` is the main entrypoint. It initializes NoneBot, bootstraps the database, syncs command config, starts background workers, and starts the FastAPI web server.
- `nextbot/` contains bot/domain logic, database models, permission resolution, external API integration, and NoneBot plugins.
- `server/` contains the FastAPI Web UI, HTML page rendering, render endpoints, and static assets.

The codebase does **not** use a heavy service/repository split. Route handlers and plugin handlers often query the database directly through `get_session()`.

---

## Directory Layout

```text
.
├── bot.py                     # NoneBot startup entrypoint
├── nextbot/
│   ├── db.py                  # SQLAlchemy models and DB bootstrap helpers
│   ├── command_config.py      # Command config persistence and validation
│   ├── permissions.py         # Permission and group inheritance resolution
│   ├── tshock_api.py          # External TShock HTTP integration
│   ├── stats.py               # Stats reads and upserts
│   ├── signin_reset.py        # Background worker
│   └── plugins/               # NoneBot command handlers by domain
│       ├── basic.py
│       ├── user_manager.py
│       ├── group_manager.py
│       ├── server_manager.py
│       └── ...
├── server/
│   ├── web_server.py          # FastAPI app creation and Uvicorn startup
│   ├── routes/                # FastAPI route modules
│   │   ├── __init__.py        # Shared API helpers
│   │   ├── webui.py
│   │   ├── webui_users.py
│   │   ├── webui_groups.py
│   │   ├── webui_servers.py
│   │   ├── webui_settings.py
│   │   ├── webui_commands.py
│   │   ├── webui_dashboard.py
│   │   └── render.py
│   ├── pages/                 # HTML page builders / render payload builders
│   ├── webui/                 # Web UI static assets and templates
│   └── assets/                # Render/static assets
└── scripts/                   # One-off maintenance and packaging scripts
```

---

## Module Organization

- Put **bot runtime / domain logic** under `nextbot/`.
- Put **HTTP routes** under `server/routes/`, usually one domain per file.
- Put **HTML page builders** under `server/pages/`.
- Put **frontend assets** under `server/webui/static/` and templates under `server/webui/templates/`.
- Keep **shared route helpers** in `server/routes/__init__.py` when multiple route files need the same API response or request-parsing behavior.
- Keep **external integration helpers** in `nextbot/` near the domain that uses them, for example `nextbot/tshock_api.py`.

This project currently prefers domain grouping over deeper layering.

---

## Naming Conventions

- Python modules use `snake_case.py`.
- Web UI route files use `webui_<domain>.py`.
- Plugin files use domain-oriented names such as `user_manager.py`, `group_manager.py`, `server_manager.py`.
- SQLAlchemy model classes use `PascalCase` and live together in `nextbot/db.py`.
- Shared helpers inside a module usually use a leading underscore, for example `_normalize_name`, `_validation_error`, `_schedule_process_restart`.

---

## Examples

### Entry and runtime wiring
- `bot.py` — bootstraps NoneBot, DB initialization, workers, and the web server.
- `server/web_server.py` — creates the FastAPI app and registers all routers.

### Route module layout
- `server/routes/webui_users.py` — CRUD-style Web UI API for users.
- `server/routes/webui_groups.py` — CRUD-style Web UI API for groups with inline validation helpers.
- `server/routes/webui_commands.py` — command config API with shared response helpers from `server/routes/__init__.py`.

### Domain / plugin organization
- `nextbot/plugins/basic.py` — general player/server commands.
- `nextbot/plugins/user_manager.py` — account and user-related commands.
- `nextbot/plugins/server_manager.py` — server management commands.

---

## Common Mistakes

- Do not invent a service/repository layer for a single route change unless the codebase already needs it. Most existing code works directly with `get_session()`.
- Do not put FastAPI-specific helpers into `nextbot/plugins/`; keep HTTP concerns under `server/`.
- Do not scatter shared API envelope logic across route files; reuse `server/routes/__init__.py` helpers instead.
- Be aware that bot runtime and Web UI runtime are coupled in one process. Startup changes in `bot.py` and `server/web_server.py` affect both.
