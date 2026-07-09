"""CardWrangler —— 跨平台 DIT 转卡 / 校验工具。

包结构（MVVM 分层）：
    models/       纯数据模型（无 UI 依赖，可单测）
    utils/        通用工具（校验和计算等）
    persistence/  任务持久化（JSON 仓库）
    services/     业务逻辑（扫描 / 拷贝 / 校验 / 占位服务）
    viewmodels/   视图模型（框架无关，自带轻量 Signal）
    views/        PySide6 界面层（仅这里依赖 Qt）
"""
from __future__ import annotations

__version__ = "0.1.0"
