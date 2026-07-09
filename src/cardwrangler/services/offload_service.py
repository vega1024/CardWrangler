"""转卡核心业务逻辑：扫描存储卡 → 拷贝文件 → 校验和比对。

该模块不依赖任何 UI 框架，可独立单测，也可被 PySide6 的 QThread 工作器调用。
支持「一源多目标」：一个文件会被拷贝到 dest_roots 中的每个目录并分别校验。
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ..models.card_job import CardJob
from ..models.item import Item, ItemStatus
from ..utils.checksum import compute_checksum

# 进度回调：传入当前 Item 与完成百分比（0–100）
ProgressFn = Callable[[Item, int], None]


def scan_source(job: CardJob) -> CardJob:
    """遍历 source_root，把所有文件建成 Item 列表（含各目标目录的完整路径）。"""
    root = Path(job.source_root)
    items: list[Item] = []
    if not root.exists():
        return job
    dest_roots = [Path(d) for d in job.dest_roots]
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    for idx, f in enumerate(paths):
        rel = f.relative_to(root)
        items.append(
            Item(
                id=f"{job.id}:{idx}",
                name=str(rel),
                source_path=str(f),
                dest_paths=[str(d / rel) for d in dest_roots],
                size=f.stat().st_size,
            )
        )
    job.items = items
    return job


def offload_item(
    item: Item,
    verify: bool,
    algorithm: str,
    on_progress: Optional[ProgressFn] = None,
) -> Item:
    """拷贝单个文件到所有目标目录，并按需做校验和比对。

    拷贝按 1MB 分块进行并回调进度；verify=True 时对每个目标分别计算校验和，
    全部与源一致才标记 VERIFIED，否则标记 FAILED。
    """
    item.status = ItemStatus.OFFLOADING
    total = item.size or 1
    n_dest = max(1, len(item.dest_paths))

    # 先计算源端校验和（仅校验模式需要）
    if verify:
        try:
            item.checksum_source = compute_checksum(item.source_path, algorithm)
        except OSError as exc:
            item.status = ItemStatus.FAILED
            item.error = str(exc)
            return item

    all_ok = True
    item.checksums_dest = []
    for di, dest in enumerate(item.dest_paths):
        d = Path(dest)
        d.parent.mkdir(parents=True, exist_ok=True)
        copied = 0
        try:
            with open(item.source_path, "rb") as src, open(d, "wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    if on_progress:
                        frac = (di + min(1.0, copied / total)) / n_dest
                        on_progress(item, min(100, int(frac * 100)))
        except OSError as exc:
            item.status = ItemStatus.FAILED
            item.error = str(exc)
            return item

        if verify:
            try:
                cd = compute_checksum(dest, algorithm)
            except OSError as exc:
                item.status = ItemStatus.FAILED
                item.error = str(exc)
                return item
            item.checksums_dest.append(cd)
            if cd != item.checksum_source:
                all_ok = False
        else:
            item.checksums_dest.append("")

    item.status = (
        ItemStatus.VERIFIED
        if (not verify or (all_ok and item.verified()))
        else ItemStatus.FAILED
    )

    if on_progress:
        on_progress(item, 100)
    return item


def offload_job(job: CardJob, on_progress: Optional[ProgressFn] = None) -> CardJob:
    """转卡整个任务：先扫描，再逐个拷贝 + 校验到所有目标目录。"""
    scan_source(job)
    for item in job.items:
        offload_item(item, job.verify_after_copy, job.checksum_algorithm, on_progress)
    job.status = (
        ItemStatus.VERIFIED
        if all(i.status == ItemStatus.VERIFIED for i in job.items)
        else ItemStatus.FAILED
    )
    return job
