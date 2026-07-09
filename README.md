# CardWrangler

跨平台的 **DIT（数字影像技师）转卡 / 校验工具**。把摄影机存储卡（CFast / SD / RED mag 等）上的素材拷贝到硬盘，并对每个文件做 **校验和比对**，确保数据完整无误。

> 技术栈：**Python 3.10+** + **PySide6（Qt）**，可同时运行在 **macOS 和 Windows**。

## 功能方向

- 扫描存储卡，列出全部待转文件
- 多线程 / 分块拷贝，实时进度
- 拷贝后可选做校验和比对（sha256 / sha1 / md5 / sha512）
- 任务列表持久化（JSON），下次打开自动恢复
- 设置：拷贝后校验开关、校验算法、默认目标目录
- **目录比对**：选择任意两个路径，递归逐文件做校验和比较（验证已有拷贝是否完整 / 两份备份是否一致）

## 目录结构（MVVM 分层）

```
CardWrangler/
├── pyproject.toml            # 工程元数据 + 入口命令
├── requirements.txt          # 依赖
├── src/
│   └── cardwrangler/
│       ├── __main__.py       # 命令行入口
│       ├── app.py            # QApplication 启动 + 样式
│       ├── models/           # 纯数据模型（Item / CardJob，无 UI 依赖）
│       ├── utils/            # 工具（checksum 计算）
│       ├── persistence/      # 任务持久化（JSON 仓库）
│       ├── services/         # 业务逻辑（扫描 / 拷贝 / 校验 + 占位服务）
│       ├── viewmodels/       # 视图模型（框架无关，自带 Signal）
│       └── views/            # PySide6 界面层（仅这里依赖 Qt）
│           ├── components/   # 可复用小组件（任务行）
│           ├── main_window.py
│           ├── sidebar_view.py / detail_view.py / settings_view.py
│           ├── compare_view.py  # 目录比对对话框
│           └── workers.py    # 后台转卡 / 比对线程
└── tests/                    # 纯逻辑单测（不依赖 Qt）
```

## 运行

```bash
# 1. 安装依赖（建议先用虚拟环境）
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. 启动
cardwrangler          # 或：python -m cardwrangler
```

Windows 上把第 1 步的 `source .venv/bin/activate` 换成 `.venv\Scripts\activate`。

## 测试

```bash
pip install -e ".[dev]"
pytest
```

测试只覆盖**不依赖 Qt 的纯逻辑**（校验和、持久化、视图模型、目录比对），
因此无需显示器也能在 CI / 命令行跑。界面层依赖 Qt，需在桌面环境验证。

## 目录比对用法

工具栏点「**比对路径**」→ 分别选择路径 A（源 / 基准）和路径 B（目标 / 副本）
→ 选校验算法 → 「开始比对」。

- 自动**递归进入子文件夹**，按相对路径逐文件配对。
- 结果分四类并着色：一致 / 不一致 / A 有 B 缺 / B 多出。
- 末尾汇总：共 N 个文件，一致 X，不一致 Y，A有B缺 Z，B多出 W。
- 比对**不拷贝任何文件**，只校验两棵树是否一致。

核心逻辑在 `services/compare_service.py` 的 `compare_paths()`，单测见
`tests/test_compare_service.py`。

## 下一步

- 真实拖拽选择多张卡 / 多目标
- 并发转卡（多卡同时）
- 生成 PDF / CSV 校验报告
- 接入云端备份（NetworkService 占位已留）
