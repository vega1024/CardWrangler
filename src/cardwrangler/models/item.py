"""单个待转卡文件的数据模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ItemStatus(str, Enum):
    """文件 / 任务状态。继承 str 以便直接 JSON 序列化。"""

    PENDING = "pending"
    OFFLOADING = "offloading"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class Item:
    """存储卡上的一个文件，以及它在各目标目录的转卡 / 校验结果。"""

    id: str
    name: str
    source_path: str
    dest_paths: List[str] = field(default_factory=list)   # 每个目标目录下的绝对路径
    size: int = 0
    status: ItemStatus = ItemStatus.PENDING
    checksum_source: str = ""
    checksums_dest: List[str] = field(default_factory=list)  # 与各 dest_paths 一一对应
    error: str = ""
    # 每个目标的拷贝 / 校验完成时间（ISO 秒）与耗时（秒），与 dest_paths 对齐
    copy_finished_at: List[str] = field(default_factory=list)
    verify_finished_at: List[str] = field(default_factory=list)
    copy_durations: List[float] = field(default_factory=list)
    verify_durations: List[float] = field(default_factory=list)

    def verified(self) -> bool:
        """所有目标目录的校验和都与源一致才算通过。"""
        if not self.checksum_source:
            return False
        return all(c and c == self.checksum_source for c in self.checksums_dest)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_path": self.source_path,
            "dest_paths": self.dest_paths,
            "size": self.size,
            "status": self.status.value,
            "checksum_source": self.checksum_source,
            "checksums_dest": self.checksums_dest,
            "error": self.error,
            "copy_finished_at": self.copy_finished_at,
            "verify_finished_at": self.verify_finished_at,
            "copy_durations": self.copy_durations,
            "verify_durations": self.verify_durations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        d = dict(d)
        d["status"] = ItemStatus(d.get("status", "pending"))
        return cls(
            id=d["id"],
            name=d["name"],
            source_path=d["source_path"],
            dest_paths=d.get("dest_paths", []),
            size=d.get("size", 0),
            status=d["status"],
            checksum_source=d.get("checksum_source", ""),
            checksums_dest=d.get("checksums_dest", []),
            error=d.get("error", ""),
            copy_finished_at=d.get("copy_finished_at", []),
            verify_finished_at=d.get("verify_finished_at", []),
            copy_durations=d.get("copy_durations", []),
            verify_durations=d.get("verify_durations", []),
        )
