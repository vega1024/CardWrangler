"""校验和计算工具（仅依赖标准库）。"""
from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_ALGORITHM = "sha256"


def compute_checksum(
    path: str | Path,
    algorithm: str = DEFAULT_ALGORITHM,
    chunk_size: int = 1 << 20,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """计算文件校验和。

    Args:
        path: 文件路径。
        algorithm: hashlib 支持的算法名，默认 sha256（可选 md5 / sha1 / sha512 等）。
        chunk_size: 分块读取大小（字节），避免大文件一次性读入内存。
        on_progress: 可选回调，传入已读取比例（0.0–1.0），用于汇报校验进度。
    """
    h = hashlib.new(algorithm)
    p = Path(path)
    size = p.stat().st_size or 1
    done = 0
    with p.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if on_progress is not None:
                on_progress(min(1.0, done / size))
    return h.hexdigest()


def checksums_match(a: str, b: str) -> bool:
    return bool(a) and a == b
