"""目录比对结果的数据模型。

用于「比较两个任意路径」功能：把两棵树按相对路径配对后，逐文件校验和
比较，每对文件对应一条 CompareEntry。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CompareStatus(str, Enum):
    """单条比对结果的状态。继承 str 以便直接 JSON 序列化。"""

    MATCH = "match"            # A、B 都存在且校验和一致
    MISMATCH = "mismatch"      # A、B 都存在但校验和不一致
    MISSING_IN_B = "missing_in_b"  # A 有、B 没有（拷贝不完整 / 缺文件）
    EXTRA_IN_B = "extra_in_b"  # B 有、A 没有（目标多出了多余文件）


@dataclass
class CompareEntry:
    """一对文件的比较结果（按相对路径配对）。"""

    rel_path: str                      # 相对路径，含子文件夹层级
    status: CompareStatus
    checksum_a: str = ""
    checksum_b: str = ""
    size_a: int = 0
    size_b: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        """是否为「无问题」状态（一致）。"""
        return self.status == CompareStatus.MATCH

    def to_dict(self) -> dict:
        return {
            "rel_path": self.rel_path,
            "status": self.status.value,
            "checksum_a": self.checksum_a,
            "checksum_b": self.checksum_b,
            "size_a": self.size_a,
            "size_b": self.size_b,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CompareEntry":
        d = dict(d)
        d["status"] = CompareStatus(d.get("status", "match"))
        return cls(
            rel_path=d["rel_path"],
            status=d["status"],
            checksum_a=d.get("checksum_a", ""),
            checksum_b=d.get("checksum_b", ""),
            size_a=d.get("size_a", 0),
            size_b=d.get("size_b", 0),
            error=d.get("error", ""),
        )


# 供 UI 显示用的中文状态文案
STATUS_LABELS = {
    CompareStatus.MATCH: "一致",
    CompareStatus.MISMATCH: "不一致",
    CompareStatus.MISSING_IN_B: "A 有 / B 缺",
    CompareStatus.EXTRA_IN_B: "B 多出",
}
