"""命令行入口：`python -m cardwrangler` 或安装后的 `cardwrangler` 命令。"""
from __future__ import annotations

from .app import run


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
