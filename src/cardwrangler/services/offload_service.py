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

    进度按「阶段」平滑推进：源校验(1) + 每个目标[拷贝(1) + 校验(1)]。
    拷贝与校验都会分块回调进度，避免界面在校验阶段「假死」。
    """
    item.status = ItemStatus.OFFLOADING
    n_dest = max(1, len(item.dest_paths))
    step = 2 if verify else 1
    total_phases = 1 + step * n_dest  # 源校验(1) + 每个目标的阶段
    cur = 0  # 当前阶段序号（0 = 源校验；无校验时直接为首个拷贝阶段）

    _last_pct = {"v": -1}

    def emit(frac: float) -> None:
        """上报进度，带 1% 节流，避免海量信号冲刷 UI 线程。"""
        if on_progress is None:
            return
        pct = min(100, int((cur + max(0.0, min(1.0, frac))) / total_phases * 100))
        if pct != _last_pct["v"]:
            _last_pct["v"] = pct
            on_progress(item, pct)

    # 先计算源端校验和（仅校验模式需要）
    if verify:
        try:
            item.checksum_source = compute_checksum(
                item.source_path, algorithm, on_progress=lambda f: emit(f)
            )
        except OSError as exc:
            item.status = ItemStatus.FAILED
            item.error = str(exc)
            return item
        cur = 1  # 源校验完成，进入首个目标阶段

    all_ok = True
    item.checksums_dest = []
    for dest in item.dest_paths:
        d = Path(dest)
        d.parent.mkdir(parents=True, exist_ok=True)
        total = item.size or 1
        copied = 0
        try:
            with open(item.source_path, "rb") as src, open(d, "wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    emit(copied / total)
        except OSError as exc:
            item.status = ItemStatus.FAILED
            item.error = str(exc)
            return item
        cur += 1  # 拷贝完成，进入校验阶段

        if verify:
            try:
                cd = compute_checksum(dest, algorithm, on_progress=lambda f: emit(f))
            except OSError as exc:
                item.status = ItemStatus.FAILED
                item.error = str(exc)
                return item
            item.checksums_dest.append(cd)
            if cd != item.checksum_source:
                all_ok = False
            cur += 1  # 校验完成
        else:
            item.checksums_dest.append("")
            cur += 1

    item.status = (
        ItemStatus.VERIFIED
        if (not verify or (all_ok and item.verified()))
        else ItemStatus.FAILED
    )

    emit(1.0)
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
