"""占位服务：模拟从远端 DIT 服务器拉取任务元数据。

后续可接入真实 API（报告生成、云端备份状态查询等）。
"""
from __future__ import annotations

from typing import Dict


class DataService:
    def fetch_job_meta(self, job_id: str) -> Dict:
        raise NotImplementedError("DataService 尚未接入真实后端")
