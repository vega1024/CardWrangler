"""任务持久化：把 CardJob 列表存成 JSON 文件。

默认存放在各平台的应用数据目录，无需数据库依赖。
未来可平滑替换为 SQLite / Core Data 等价物，只要实现同样的 load/save 接口。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

from ..models.card_job import CardJob


def app_data_dir() -> Path:
    """返回跨平台的应用数据目录（不存在则创建）。"""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "CardWrangler"
    elif sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "CardWrangler"
    else:
        base = Path.home() / ".cardwrangler"
    base.mkdir(parents=True, exist_ok=True)
    return base


class JobRepository:
    """把任务列表读写到单个 JSON 文件。"""

    def __init__(self, path: Optional[str | Path] = None):
        self.path = Path(path) if path else (app_data_dir() / "jobs.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: List[CardJob] = []
        self.load()

    @classmethod
    def default(cls) -> "JobRepository":
        return cls()

    def load(self) -> List[CardJob]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._jobs = [CardJob.from_dict(j) for j in data.get("jobs", [])]
            except (json.JSONDecodeError, TypeError, ValueError):
                # 文件损坏时不崩溃，退回空列表
                self._jobs = []
        return self._jobs

    def save(self, jobs: Optional[List[CardJob]] = None) -> None:
        if jobs is not None:
            self._jobs = list(jobs)
        data = {"jobs": [j.to_dict() for j in self._jobs]}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def all(self) -> List[CardJob]:
        return list(self._jobs)

    def find(self, job_id: str) -> Optional[CardJob]:
        for j in self._jobs:
            if j.id == job_id:
                return j
        return None
