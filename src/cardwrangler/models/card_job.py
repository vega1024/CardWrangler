"""一次「转卡任务」（一张存储卡 → 一块硬盘）的数据模型。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .item import Item, ItemStatus


@dataclass
class CardJob:
    """一条转卡任务：包含若干 Item（文件）以及整体配置。"""

    id: str
    label: str
    source_root: str
    dest_root: str
    items: List[Item] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    verify_after_copy: bool = True
    checksum_algorithm: str = "sha256"
    status: ItemStatus = ItemStatus.PENDING

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
            "dest_root": self.dest_root,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at,
            "verify_after_copy": self.verify_after_copy,
            "checksum_algorithm": self.checksum_algorithm,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CardJob":
        d = dict(d)
        d["status"] = ItemStatus(d.get("status", "pending"))
        d["items"] = [Item.from_dict(i) for i in d.get("items", [])]
        return cls(
            id=d["id"],
            label=d["label"],
            source_root=d["source_root"],
            dest_root=d["dest_root"],
            items=d["items"],
            created_at=d.get("created_at", ""),
            verify_after_copy=d.get("verify_after_copy", True),
            checksum_algorithm=d.get("checksum_algorithm", "sha256"),
            status=d["status"],
        )

    @staticmethod
    def new(label: str, source_root: str, dest_root: str) -> "CardJob":
        """工厂方法：生成带唯一 id 的新任务。"""
        return CardJob(
            id=uuid.uuid4().hex[:12],
            label=label,
            source_root=source_root,
            dest_root=dest_root,
        )
