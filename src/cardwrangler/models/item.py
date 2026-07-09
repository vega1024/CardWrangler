"""单个待转卡文件的数据模型。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ItemStatus(str, Enum):
    """文件 / 任务状态。继承 str 以便直接 JSON 序列化。"""

    PENDING = "pending"
    OFFLOADING = "offloading"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class Item:
    """存储卡上的一个文件，以及它的转卡 / 校验结果。"""

    id: str
    name: str
    source_path: str
    dest_path: str = ""
    size: int = 0
    status: ItemStatus = ItemStatus.PENDING
    checksum_source: str = ""
    checksum_dest: str = ""
    error: str = ""

    def verified(self) -> bool:
        """源与目标校验和一致才算校验通过。"""
        return bool(self.checksum_source) and self.checksum_source == self.checksum_dest

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "size": self.size,
            "status": self.status.value,
            "checksum_source": self.checksum_source,
            "checksum_dest": self.checksum_dest,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        d = dict(d)
        d["status"] = ItemStatus(d.get("status", "pending"))
        return cls(
            id=d["id"],
            name=d["name"],
            source_path=d["source_path"],
            dest_path=d.get("dest_path", ""),
            size=d.get("size", 0),
            status=d["status"],
            checksum_source=d.get("checksum_source", ""),
            checksum_dest=d.get("checksum_dest", ""),
            error=d.get("error", ""),
        )
