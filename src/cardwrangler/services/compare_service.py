"""目录比对服务：对两个任意路径递归逐文件做校验和比对。

与 offload（转卡）不同，这里不拷贝任何东西，只「验证两棵树是否一致」——
例如确认一次已有的拷贝是否完整、或两份备份是否相同。
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..models.compare_result import CompareEntry, CompareStatus
from ..utils.checksum import compute_checksum, DEFAULT_ALGORITHM

# 进度回调：传入当前 CompareEntry 与完成百分比（0–100）
ProgressFn = Callable[[CompareEntry, int], None]


def collect_files(root: Path) -> Dict[str, Path]:
    """递归收集 root 下所有文件，返回 {相对路径: 绝对路径}。

    相对路径保留完整的子文件夹层级（例如 "CLIPS/SUB/0001.MXF"），
    因此比对时会按「相对路径」配对，天然支持子文件夹递归比较。
    """
    root = Path(root)
    out: Dict[str, Path] = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = p
    return out


def compare_paths(
    path_a: str,
    path_b: str,
    algorithm: str = DEFAULT_ALGORITHM,
    on_progress: Optional[ProgressFn] = None,
) -> List[CompareEntry]:
    """比对两个路径，逐文件（含子文件夹）进行校验和比较。

    配对规则：以相对路径为 key。
    - A、B 都有 → 计算两边校验和，一致为 MATCH，否则 MISMATCH
    - 仅 A 有   → MISSING_IN_B（B 缺文件，拷贝不完整）
    - 仅 B 有   → EXTRA_IN_B（B 多出文件）

    Args:
        path_a: 路径 A（通常当作「源 / 基准」）。
        path_b: 路径 B（通常当作「目标 / 副本」）。
        algorithm: 校验和算法，默认 sha256。
        on_progress: 每比对完一个文件回调一次 (CompareEntry, 百分比)。

    Returns:
        按相对路径排序的 CompareEntry 列表。
    """
    a_files = collect_files(Path(path_a))
    b_files = collect_files(Path(path_b))

    all_rel = sorted(set(a_files) | set(b_files))
    total = len(all_rel) or 1
    results: List[CompareEntry] = []

    for idx, rel in enumerate(all_rel, start=1):
        pa = a_files.get(rel)
        pb = b_files.get(rel)

        if pa is not None and pb is not None:
            try:
                ca = compute_checksum(pa, algorithm)
                cb = compute_checksum(pb, algorithm)
                status = CompareStatus.MATCH if ca == cb else CompareStatus.MISMATCH
                entry = CompareEntry(
                    rel_path=rel,
                    status=status,
                    checksum_a=ca,
                    checksum_b=cb,
                    size_a=pa.stat().st_size,
                    size_b=pb.stat().st_size,
                )
            except OSError as exc:
                entry = CompareEntry(
                    rel_path=rel,
                    status=CompareStatus.MISMATCH,
                    error=str(exc),
                )
        elif pa is not None:
            entry = CompareEntry(
                rel_path=rel,
                status=CompareStatus.MISSING_IN_B,
                size_a=pa.stat().st_size,
            )
        else:
            entry = CompareEntry(
                rel_path=rel,
                status=CompareStatus.EXTRA_IN_B,
                size_b=pb.stat().st_size,
            )

        results.append(entry)
        if on_progress:
            on_progress(entry, min(100, int(idx / total * 100)))

    return results
