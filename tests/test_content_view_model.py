"""ContentViewModel 测试（框架无关，不依赖 Qt）。"""
from __future__ import annotations

from cardwrangler.models.card_job import CardJob
from cardwrangler.models.item import Item
from cardwrangler.persistence.repository import JobRepository
from cardwrangler.viewmodels.content_view_model import ContentViewModel


def _spy():
    events = []
    return events, lambda *a, **k: events.append((a, k))


def test_add_job_emits_jobs_changed_and_persists(tmp_path):
    repo = JobRepository(tmp_path / "jobs.json")
    vm = ContentViewModel(repo)
    events, slot = _spy()
    vm.jobs_changed.connect(slot)

    job = CardJob.new("CardA", "/src", "/dst")
    vm.add_job(job)

    assert len(vm.jobs) == 1
    assert len(events) == 1
    # 重新加载仓库，确认已落盘
    assert len(JobRepository(tmp_path / "jobs.json").all()) == 1


def test_select_and_remove_job(tmp_path):
    repo = JobRepository(tmp_path / "jobs.json")
    vm = ContentViewModel(repo)
    job = CardJob.new("CardA", "/src", "/dst")
    vm.add_job(job)

    vm.select_job(job)
    assert vm.selected_job is job

    vm.remove_job(job)
    assert job not in vm.jobs
    assert vm.selected_job is None


def test_report_progress_forwards_to_signal(tmp_path):
    repo = JobRepository(tmp_path / "jobs.json")
    vm = ContentViewModel(repo)
    events, slot = _spy()
    vm.progress.connect(slot)

    item = Item(id="x:0", name="a.mxf", source_path="/s/a.mxf", size=10)
    vm.report_progress(item, 42)

    assert events and events[0][0] == (item, 42)
