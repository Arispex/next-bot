"""Resolve the directory used for persistent state files.

Persistent state lives in three files at the data directory root:
- ``.env``                 — runtime configuration (auto-created on first launch)
- ``app.db``               — SQLite database (auto-created and migrated on launch)
- ``.webui_auth.json``     — WebUI admin credentials (auto-generated on first launch)

By default the data directory is the project root, which preserves backwards
compatibility with bare-metal / source-checkout deployments. Set the
``NEXTBOT_DATA_DIR`` environment variable to relocate state — Docker images use
``/app/data`` so the host can mount a single volume to persist all three files.

The directory is created (with parents) at import time so downstream consumers
can treat the path as guaranteed-to-exist.
"""

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_data_dir() -> Path:
    raw = os.environ.get("NEXTBOT_DATA_DIR", "").strip()
    path = Path(raw).expanduser().resolve() if raw else _PROJECT_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR: Path = _resolve_data_dir()
