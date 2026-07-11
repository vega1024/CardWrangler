"""生成转卡 / 校验报告（当前为 CSV）。"""
from __future__ import annotations

from typing import List

from ..models.card_job import CardJob


def _csv(value) -> str:
    """转义 CSV 字段：含逗号 / 引号 / 换行时用双引号包裹。"""
    s = "" if value is None else str(value)
    if any(ch in s for ch in [",", '"', "\n"]):
        return '"' + s.replace('"', '""') + '"'
    return s


def build_report_csv(jobs: List[CardJob]) -> str:
    """把每个任务、每个目标盘汇成一行 CSV。

    列：任务, 目标序号, 目标路径, 拷贝状态, 拷贝完成时间, 拷贝耗时(秒),
        校验状态, 校验算法, 校验完成时间, 校验耗时(秒), 文件数
    """
    header = [
        "任务", "目标序号", "目标路径", "拷贝状态", "拷贝完成时间", "拷贝耗时(秒)",
        "校验状态", "校验算法", "校验完成时间", "校验耗时(秒)", "文件数",
    ]
    lines = [",".join(header)]
    for job in jobs:
        n = len(job.dest_roots)
        for di in range(n):
            root = job.dest_roots[di]
            copy_at = job.copy_finished_at[di] if di < len(job.copy_finished_at) else ""
            copy_dur = job.copy_durations[di] if di < len(job.copy_durations) else 0.0
            copy_status = "已完成" if copy_at else "待拷贝"

            if not job.verify_after_copy:
                v_status, v_at, v_dur, algo = "未校验", "", 0.0, ""
            else:
                v_at = job.verify_finished_at[di] if di < len(job.verify_finished_at) else ""
                v_status = "已完成" if v_at else "待校验"
                v_dur = job.verify_durations[di] if di < len(job.verify_durations) else 0.0
                algo = job.checksum_algorithm

            lines.append(
                ",".join(
                    [
                        _csv(job.label),
                        _csv(str(di + 1)),
                        _csv(root),
                        _csv(copy_status),
                        _csv(copy_at),
                        _csv(f"{copy_dur:.1f}"),
                        _csv(v_status),
                        _csv(algo),
                        _csv(v_at),
                        _csv(f"{v_dur:.1f}"),
                        _csv(str(len(job.items))),
                    ]
                )
            )
    return "\n".join(lines)
