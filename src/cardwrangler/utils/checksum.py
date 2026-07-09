"""校验和计算工具（仅依赖标准库）。"""
from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_ALGORITHM = "sha256"


def compute_checksum(path: str | Path, algorithm: str = DEFAULT_ALGORITHM, chunk_size: int = 1 << 20) -> str:
    """计算文件校验和。

    Args:
        path: 文件路径。
        algorithm: hashlib 支持的算法名，默认 sha256（可选 md5 / sha1 / sha512 等）。
        chunk_size: 分块读取大小（字节），避免大文件一次性读入内存。
    """
    h = hashlib.new(algorithm)
    p = Path(path)
    with p.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def checksums_match(a: str, b: str) -> bool:
    return bool(a) and a == b
