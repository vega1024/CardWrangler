"""一次「转卡任务」（一张存储卡 → 一个或多个目标硬盘）的数据模型。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .item import Item, ItemStatus


@dataclass
class CardJob:
    """一条转卡任务：包含若干 Item（文件）以及整体配置（可含多个目标目录）。"""

    id: str
    label: str
    source_root: str
    dest_roots: List[str] = field(default_factory=list)   # 一源多目标
    items: List[Item] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    verify_after_copy: bool = True
    checksum_algorithm: str = "md5"
    status: ItemStatus = ItemStatus.PENDING
    # 任务级时间
    finished_at: str = ""           # 任务完成时间（ISO 秒）
    duration_seconds: float = 0.0   # 任务总耗时（秒）
    # 每个目标的拷贝 / 校验完成时间（ISO 秒）与耗时（秒），与 dest_roots 对齐
    copy_finished_at: List[str] = field(default_factory=list)
    verify_finished_at: List[str] = field(default_factory=list)
    copy_durations: List[float] = field(default_factory=list)
    verify_durations: List[float] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.items)

    @property
    def copied_bytes(self) -> int:
        return sum(i.size for i in self.items if i.status != ItemStatus.PENDING)

    @property
    def verified_count(self) -> int:
        return sum(1 for i in self.items if i.status == ItemStatus.VERIFIED)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "source_root": self.source_root,
            "dest_roots": self.dest_roots,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at,
            "verify_after_copy": self.verify_after_copy,
            "checksum_algorithm": self.checksum_algorithm,
            "status": self.status.value,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "copy_finished_at": self.copy_finished_at,
            "verify_finished_at": self.verify_finished_at,
            "copy_durations": self.copy_durations,
            "verify_durations": self.verify_durations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CardJob":
        d = dict(d)
        d["status"] = ItemStatus(d.get("status", "pending"))
        d["items"] = [Item.from_dict(i) for i in d.get("items", [])]
        # 兼容旧版单目标 JSON（dest_root: str）
        dest = d.get("dest_roots")
        if not dest:
            single = d.get("dest_root")
            dest = [single] if single else []
        return cls(
            id=d["id"],
            label=d["label"],
            source_root=d["source_root"],
            dest_roots=list(dest),
            items=d["items"],
            created_at=d.get("created_at", ""),
            verify_after_copy=d.get("verify_after_copy", True),
            checksum_algorithm=d.get("checksum_algorithm", "md5"),
            status=d["status"],
            finished_at=d.get("finished_at", ""),
            duration_seconds=d.get("duration_seconds", 0.0),
            copy_finished_at=d.get("copy_finished_at", []),
            verify_finished_at=d.get("verify_finished_at", []),
            copy_durations=d.get("copy_durations", []),
            verify_durations=d.get("verify_durations", []),
        )

    @staticmethod
    def new(label: str, source_root: str, dest_roots: List[str]) -> "CardJob":
        """工厂方法：生成带唯一 id 的新任务。dest_roots 为目录列表（可多个）。"""
        return CardJob(
            id=uuid.uuid4().hex[:12],
            label=label,
            source_root=source_root,
            dest_roots=list(dest_roots),
        )
