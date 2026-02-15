from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app.db"


def _get_user_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute('PRAGMA table_info("user")').fetchall()
    return {str(row[1]) for row in rows}


def main() -> None:
    db_path = Path(DB_PATH).resolve()
    if not db_path.exists():
        print(f"database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    try:
        columns = _get_user_columns(conn)
        if "coins" in columns:
            print("skip: column user.coins already exists")
            return

        conn.execute('ALTER TABLE "user" ADD COLUMN "coins" INTEGER NOT NULL DEFAULT 0')
        conn.commit()
        print("done: added column user.coins INTEGER NOT NULL DEFAULT 0")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
