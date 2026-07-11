"""转卡核心业务逻辑：扫描存储卡 → 拷贝文件 → 校验和比对。

该模块不依赖任何 UI 框架，可独立单测，也可被 PySide6 的 QThread 工作器调用。
支持「一源多目标」：一个文件会被拷贝到 dest_roots 中的每个目录并分别校验。
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..models.card_job import CardJob
from ..models.item import Item, ItemStatus
from ..utils.checksum import compute_checksum

# 进度回调：传入当前 Item 与完成百分比（0–100）
ProgressFn = Callable[[Item, int], None]


def _now() -> str:
    """当前时间，ISO 格式到秒，用于记录拷贝 / 校验完成时刻。"""
    return datetime.now().isoformat(timespec="seconds")


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
    n = len(item.dest_paths)
    # 初始化每目标的时间 / 耗时记录（与 dest_paths 对齐）
    item.copy_finished_at = [""] * n
    item.verify_finished_at = [""] * n
    item.copy_durations = [0.0] * n
    item.verify_durations = [0.0] * n
    n_dest = max(1, n)
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
    for di, dest in enumerate(item.dest_paths):
        d = Path(dest)
        d.parent.mkdir(parents=True, exist_ok=True)
        total = item.size or 1
        copied = 0
        t_copy = time.monotonic()
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
        item.copy_durations[di] = time.monotonic() - t_copy
        item.copy_finished_at[di] = _now()
        cur += 1  # 拷贝完成，进入校验阶段

        if verify:
            t_verify = time.monotonic()
            try:
                cd = compute_checksum(dest, algorithm, on_progress=lambda f: emit(f))
            except OSError as exc:
                item.status = ItemStatus.FAILED
                item.error = str(exc)
                return item
            item.verify_durations[di] = time.monotonic() - t_verify
            item.verify_finished_at[di] = _now()
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
    """转卡整个任务：先扫描，再逐个拷贝 + 校验到所有目标目录。

    结束后把每个 Item 的「每目标」拷贝 / 校验耗时与时间聚合到任务级字段，
    方便详情界面（目标盘表格）直接展示每个目标的完成时刻与耗时。
    """
    overall_start = time.monotonic()
    scan_source(job)
    n = len(job.dest_roots)
    for item in job.items:
        offload_item(item, job.verify_after_copy, job.checksum_algorithm, on_progress)

    def _agg(getter) -> list:
        return [getter(di) for di in range(n)]

    job.copy_durations = [
        sum(i.copy_durations[di] for i in job.items) for di in range(n)
    ]
    job.verify_durations = [
        sum(i.verify_durations[di] for i in job.items) for di in range(n)
    ]
    job.copy_finished_at = _agg(
        lambda di: max(
            (i.copy_finished_at[di] for i in job.items if i.copy_finished_at[di]),
            default="",
        )
    )
    job.verify_finished_at = _agg(
        lambda di: max(
            (i.verify_finished_at[di] for i in job.items if i.verify_finished_at[di]),
            default="",
        )
    )
    job.finished_at = _now()
    job.duration_seconds = time.monotonic() - overall_start
    job.status = (
        ItemStatus.VERIFIED
        if all(i.status == ItemStatus.VERIFIED for i in job.items)
        else ItemStatus.FAILED
    )
    return job
