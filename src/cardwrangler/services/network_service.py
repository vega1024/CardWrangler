"""占位服务：网络可达性 / 云端上传等检查。

后续可接入对象存储 SDK（S3 / COS 等）。
"""
from __future__ import annotations


class NetworkService:
    def is_reachable(self, host: str = "github.com") -> bool:
        raise NotImplementedError("NetworkService 尚未实现")
