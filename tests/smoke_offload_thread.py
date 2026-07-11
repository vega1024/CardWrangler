"""offscreen 冒烟：真实跑一遍 offload 后台线程，验证进度信号不会跨线程操作 GUI。

复现思路：之前 worker.progress 连到普通 lambda，跨线程时 slot 在子线程执行，
子线程操作 GUI → "QPaintDevice: Cannot destroy paint device..." + segfault。
修复后 progress 连到 MainWindow 绑定 slot + QueuedConnection，slot 应在主线程执行。

此脚本建临时源/目标目录、造几个文件，构造 CardJob，走 MainWindow 的 offload 流程，
用 QEventLoop 等 worker 完成；同时断言进度回调发生在主线程。
"""
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from cardwrangler.models.card_job import CardJob
from cardwrangler.viewmodels.content_view_model import ContentViewModel
from cardwrangler.persistence.repository import JobRepository
from cardwrangler.views.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    main_thread = threading.get_ident()
    progress_threads = []
    finished = {"ok": False}

    tmp = Path(tempfile.mkdtemp(prefix="cw_smoke_"))
    src = tmp / "SRC"
    dst1 = tmp / "DST1"
    dst2 = tmp / "DST2"
    (src / "CLIPS").mkdir(parents=True)
    for i in range(4):
        (src / "CLIPS" / f"{i:04d}.MXF").write_bytes(b"x" * (100_000 + i))
    dst1.mkdir()
    dst2.mkdir()

    # 用独立临时仓库，避免污染用户 ~/.cardwrangler/jobs.json
    repo = JobRepository(path=str(tmp / "jobs.json"))
    vm = ContentViewModel(repository=repo)
    win = MainWindow(vm)

    # 记录进度回调所在线程
    orig = win._on_worker_progress
    def spy(item, pct):
        progress_threads.append(threading.get_ident())
        orig(item, pct)
    win._on_worker_progress = spy  # type: ignore

    job = CardJob.new("smoke", str(src), [str(dst1), str(dst2)])
    job.verify_after_copy = True
    job.checksum_algorithm = "md5"
    vm.add_job(job)
    vm.select_job(job)

    loop = QEventLoop()

    def on_done(_job):
        finished["ok"] = True
        QTimer.singleShot(50, loop.quit)

    win.worker_done_hook = on_done  # 备用
    # 直接监听 vm 的 jobs_changed 不可靠，改为 hook finalize：轮询 is_busy
    def poll():
        if not vm.is_busy and (progress_threads or finished["ok"]):
            loop.quit()
        else:
            QTimer.singleShot(50, poll)

    win._start_offload()
    QTimer.singleShot(50, poll)
    # 超时兜底 15s
    QTimer.singleShot(15000, loop.quit)
    loop.exec()

    # 断言
    assert progress_threads, "FAIL: 未收到任何进度回调（offload 可能没跑）"
    bad = [t for t in progress_threads if t != main_thread]
    assert not bad, f"FAIL: 有 {len(bad)} 次进度回调发生在子线程（跨线程操作 GUI 会崩溃）"
    assert not vm.is_busy, "FAIL: offload 结束后 is_busy 仍为 True"
    # 聚合字段应被 offload_job 填充（每目标 2 个）
    assert len(job.copy_finished_at) == 2 and all(job.copy_finished_at), (
        f"FAIL: 拷贝完成时间戳未聚合，实际 {job.copy_finished_at}"
    )
    assert len(job.verify_finished_at) == 2 and all(job.verify_finished_at), (
        f"FAIL: 校验完成时间戳未聚合，实际 {job.verify_finished_at}"
    )
    assert job.finished_at, "FAIL: job.finished_at 未设置"
    assert job.duration_seconds > 0, "FAIL: job.duration_seconds 未设置"

    print("PASS: offload 后台线程完成，进度回调全部在主线程，聚合字段已填充")
    print(f"  进度回调次数 = {len(progress_threads)}，全部主线程 = True")
    print(f"  拷贝完成时间戳 = {job.copy_finished_at}")
    print(f"  校验完成时间戳 = {job.verify_finished_at}")
    print(f"  任务完成时间 = {job.finished_at}，耗时 = {job.duration_seconds:.3f}s")


if __name__ == "__main__":
    main()
