"""checksum 工具测试（纯标准库，不依赖 Qt）。"""
from __future__ import annotations

import hashlib

from cardwrangler.utils.checksum import compute_checksum, checksums_match


def test_compute_checksum_matches_hashlib(tmp_path):
    f = tmp_path / "sample.bin"
    data = b"CardWrangler rocks " * 1000
    f.write_bytes(data)

    got = compute_checksum(f, "sha256")
    expected = hashlib.sha256(data).hexdigest()
    assert got == expected


def test_compute_checksum_is_stable(tmp_path):
    f = tmp_path / "sample.bin"
    f.write_bytes(b"hello world")

    assert compute_checksum(f, "md5") == compute_checksum(f, "md5")
    assert compute_checksum(f, "md5") == hashlib.md5(b"hello world").hexdigest()


def test_checksums_match():
    assert checksums_match("abc", "abc")
    assert not checksums_match("abc", "abd")
    assert not checksums_match("", "abc")
