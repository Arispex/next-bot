#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


def get_file_list(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            "-co",
            "--exclude-standard",
            "-z",
        ],
        capture_output=True,
        check=True,
    )
    raw_items = [item for item in result.stdout.decode("utf-8", errors="ignore").split("\0") if item]
    files: list[Path] = []
    for item in raw_items:
        path = repo_root / item
        if path.is_file():
            files.append(path)
    return files


def build_zip(repo_root: Path, output_path: Path) -> int:
    files = get_file_list(repo_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(repo_root)
            zf.write(file_path, arcname)

    return len(files)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="打包当前项目为 release zip（排除 ignore 文件）")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="输出 zip 路径，默认在项目根目录自动生成",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = repo_root / f"release-{timestamp}.zip"

    file_count = build_zip(repo_root, output_path)
    print(f"打包完成：{output_path}")
    print(f"文件数量：{file_count}")


if __name__ == "__main__":
    main()
