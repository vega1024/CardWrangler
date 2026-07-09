"""compare_paths 纯逻辑测试（不依赖 Qt）。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from cardwrangler.models.compare_result import CompareEntry, CompareStatus
from cardwrangler.services.compare_service import collect_files, compare_paths


def _write(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _tree() -> tuple[Path, Path]:
    """造两棵目录：A 为基准，B 大部分一致但故意制造几种差异。"""
    root = Path(tempfile.mkdtemp())
    a = root / "A"
    b = root / "B"
    # 一致（含子文件夹嵌套）
    _write(a / "CLIPS/0001.MXF", b"hello world")
    _write(b / "CLIPS/0001.MXF", b"hello world")
    _write(a / "SUB/deep/file.txt", b"nested content")
    _write(b / "SUB/deep/file.txt", b"nested content")
    # 不一致：内容不同
    _write(a / "diff.MXF", b"original")
    _write(b / "diff.MXF", b"tampered")
    # A 有、B 缺
    _write(a / "missing.MXF", b"should be in b")
    # B 多出
    _write(b / "extra.MXF", b"only in b")
    return a, b


def test_collect_files_recurses() -> None:
    a, _ = _tree()
    files = collect_files(a)
    assert set(files) == {
        "CLIPS/0001.MXF",
        "SUB/deep/file.txt",
        "diff.MXF",
        "missing.MXF",
    }


def test_compare_paths_all_cases() -> None:
    a, b = _tree()
    results = {e.rel_path: e for e in compare_paths(a, b, "sha256")}

    assert results["CLIPS/0001.MXF"].status == CompareStatus.MATCH
    assert results["SUB/deep/file.txt"].status == CompareStatus.MATCH
    assert results["diff.MXF"].status == CompareStatus.MISMATCH
    assert results["missing.MXF"].status == CompareStatus.MISSING_IN_B
    assert results["extra.MXF"].status == CompareStatus.EXTRA_IN_B

    # 嵌套子文件夹也逐一比对到了
    assert "SUB/deep/file.txt" in results
    # 校验和确实算出来了且一致对
    assert results["CLIPS/0001.MXF"].checksum_a == results["CLIPS/0001.MXF"].checksum_b


def test_compare_paths_progress_called() -> None:
    a, b = _tree()
    seq: list[tuple[CompareEntry, int]] = []
    compare_paths(a, b, "sha256", on_progress=lambda e, p: seq.append((e, p)))

    assert len(seq) == len(set(collect_files(a)) | set(collect_files(b)))
    # 百分比单调递增且终止于 100
    pcts = [p for _, p in seq]
    assert pcts == sorted(pcts)
    assert pcts[-1] == 100


def test_missing_path_is_empty() -> None:
    root = Path(tempfile.mkdtemp())
    missing = root / "does_not_exist"
    other = root / "other"
    _write(other / "x.txt", b"x")
    results = compare_paths(missing, other, "sha256")
    assert len(results) == 1
    assert results[0].status == CompareStatus.EXTRA_IN_B
