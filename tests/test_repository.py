"""JobRepository 持久化测试。"""
from __future__ import annotations

from cardwrangler.models.card_job import CardJob
from cardwrangler.models.item import Item, ItemStatus
from cardwrangler.persistence.repository import JobRepository


def _make_job() -> CardJob:
    job = CardJob.new("TestCard", "/src", ["/dst"])
    job.items = [
        Item(id=f"{job.id}:0", name="a.mxf", source_path="/src/a.mxf", size=10),
        Item(id=f"{job.id}:1", name="b.mxf", source_path="/src/b.mxf", size=20),
    ]
    job.items[0].status = ItemStatus.VERIFIED
    job.items[0].checksum_source = "deadbeef"
    job.items[0].checksums_dest = ["deadbeef"]
    return job


def test_save_then_reload_preserves_data(tmp_path):
    path = tmp_path / "jobs.json"
    repo = JobRepository(path)
    job = _make_job()
    repo.save([job])

    reloaded = JobRepository(path)
    assert len(reloaded.all()) == 1
    got = reloaded.all()[0]
    assert got.label == "TestCard"
    assert len(got.items) == 2
    assert got.items[0].status == ItemStatus.VERIFIED
    assert got.items[0].checksum_source == "deadbeef"


def test_corrupt_file_falls_back_to_empty(tmp_path):
    path = tmp_path / "jobs.json"
    path.write_text("{ this is not json", encoding="utf-8")
    repo = JobRepository(path)
    assert repo.all() == []
