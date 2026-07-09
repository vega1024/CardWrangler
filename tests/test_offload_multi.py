"""转卡多目标测试：一个源拷贝到多个目标目录并分别校验。"""
from __future__ import annotations

from pathlib import Path

from cardwrangler.models.card_job import CardJob
from cardwrangler.models.item import ItemStatus
from cardwrangler.services.offload_service import offload_job, scan_source


def _tree(root: Path) -> None:
    (root / "A").mkdir(parents=True, exist_ok=True)
    (root / "A" / "x.mxf").write_bytes(b"hello")
    (root / "B").mkdir(parents=True, exist_ok=True)
    (root / "B" / "y.mxf").write_bytes(b"world" * 1000)


def test_offload_to_multiple_targets(tmp_path):
    src = tmp_path / "card"
    _tree(src)
    d1 = tmp_path / "dest1"
    d2 = tmp_path / "dest2"

    job = CardJob.new("Card", str(src), [str(d1), str(d2)])
    job.verify_after_copy = True
    job.checksum_algorithm = "sha256"

    offload_job(job)

    # 两个目标目录都应存在且内容一致
    for d in (d1, d2):
        assert (d / "A" / "x.mxf").read_bytes() == b"hello"
        assert (d / "B" / "y.mxf").read_bytes() == b"world" * 1000

    # 每个 item 应有两个目标路径、两个目标校验和，且全部 VERIFIED
    assert len(job.items) == 2
    for it in job.items:
        assert len(it.dest_paths) == 2
        assert len(it.checksums_dest) == 2
        assert it.status == ItemStatus.VERIFIED
        assert it.verified()
        assert it.checksums_dest[0] == it.checksums_dest[1]


def test_scan_source_builds_per_target_dest_paths(tmp_path):
    src = tmp_path / "card"
    _tree(src)
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    job = CardJob.new("Card", str(src), [str(d1), str(d2)])
    scan_source(job)
    rels = sorted(i.name for i in job.items)
    assert rels == ["A/x.mxf", "B/y.mxf"]
    for it in job.items:
        # 每个 item 应有两个目标路径，且都以对应相对路径结尾
        assert len(it.dest_paths) == 2
        assert it.dest_paths[0] == str(d1 / it.name)
        assert it.dest_paths[1] == str(d2 / it.name)
