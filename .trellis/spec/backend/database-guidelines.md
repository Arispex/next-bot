# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

This project uses SQLite with SQLAlchemy 2.x declarative models.

- Database file: `app.db`
- ORM/models: `nextbot/db.py`
- Session pattern: `session = get_session()` with manual `try/finally` close
- Schema bootstrap and lightweight schema patching also live in `nextbot/db.py`

There is currently **no Alembic or formal migration framework** in the repo.

---

## ORM and Session Pattern

- Models inherit from `Base(DeclarativeBase)` in `nextbot/db.py`.
- Sessions are created with `get_session()`.
- Route and runtime code usually manages session lifecycle manually:
  - open session
  - query / mutate
  - `commit()` on success
  - `rollback()` in `except` for writes
  - always `close()` in `finally`

### Examples
- `nextbot/db.py` — model definitions, engine creation, and `get_session()`.
- `server/routes/webui_users.py` — typical CRUD transaction pattern.
- `server/routes/webui_groups.py` — validation + DB write + rollback pattern.
- `server/routes/webui_servers.py` — create/update/delete flows using explicit commit/rollback.

---

## Query Patterns

- Reads usually use direct SQLAlchemy ORM queries in handlers, for example:
  - `session.query(User).filter(...).first()`
  - `session.query(Group).order_by(...).all()`
- List endpoints usually:
  - load rows
  - serialize to dicts
  - optionally filter in Python
  - apply pagination after serialization
- Stats upserts use SQLite-specific conflict handling where needed.

### Examples
- `server/routes/webui_users.py` — list, create, update, delete queries.
- `server/routes/webui_groups.py` — grouped count query via `func.count` and CRUD queries.
- `nextbot/stats.py` — SQLite `insert(...).on_conflict_do_update(...)` upsert pattern.
- `nextbot/permissions.py` — permission resolution using direct group/user lookups.

---

## Migrations and Schema Evolution

This project currently uses **bootstrap helpers + raw SQLite schema patching**, not a migration framework.

- `Base.metadata.create_all(get_engine())` creates missing tables.
- `ensure_*_schema()` helpers patch existing SQLite tables using `sqlite3` and `ALTER TABLE`.
- Default seed data is created by helper functions such as `ensure_default_groups()` and `ensure_default_stats()`.

### Examples
- `nextbot/db.py:101-107` style flow — `init_db()` bootstraps tables and defaults.
- `nextbot/db.py:157-174` — `ensure_command_config_schema()` adds a missing column with raw SQLite.
- `nextbot/db.py:177-207` — `ensure_user_signin_schema()` adds new columns with raw SQLite.
- `bot.py` — startup path runs `create_all(...)` and the `ensure_*` helpers.

### Guidance
- If you add a column, follow the existing `ensure_*_schema()` pattern unless the project adopts a real migration tool later.
- Keep schema patch helpers idempotent.
- Commit after write operations that seed defaults.

---

## Naming Conventions

- Tables are singular or domain-specific, not strictly plural:
  - `server`
  - `user`
  - `user_group`
  - `command_config`
  - `system_stat`
- Model classes use `PascalCase`.
- Columns use `snake_case`.
- Date/time fields typically end with `_at`, such as `created_at`, `updated_at`, `last_synced_at`.
- Some multi-value fields are stored as comma-separated strings instead of join tables:
  - `User.permissions`
  - `User.group`
  - `Group.permissions`
  - `Group.inherits`
- Some structured fields are stored as JSON text:
  - `CommandConfig.param_schema_json`
  - `CommandConfig.param_values_json`

### Examples
- `nextbot/db.py` — all table and column naming conventions.
- `nextbot/command_config.py` — JSON text columns converted into runtime dict structures.
- `nextbot/permissions.py` — comma-separated permission/inheritance parsing.

---

## Common Mistakes

- Do not assume autoincrement everywhere. `Server.id` is manually managed (`autoincrement=False`) and delete logic compacts IDs.
- Do not add Alembic-style migration docs or commands unless the project actually adopts Alembic.
- Be careful with comma-separated permission / inheritance fields; they are normalized in code and should not be treated like relational join tables.
- Do not forget `rollback()` in write-path `except` blocks.
- Do not leave sessions open; the existing pattern always closes them explicitly.
