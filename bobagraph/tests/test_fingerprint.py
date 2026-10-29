"""Tests for bobagraph_setup fingerprint functions.

Imports the functions directly from bobagraph_setup (stdlib only, no extra deps).
"""
import sys
import json
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from bobagraph_setup import (
    compute_fingerprint,
    save_fingerprint,
    load_fingerprint,
    check_staleness,
    _fingerprint_file,
)


def _make_repo(tmp: Path, files: dict[str, str]) -> Path:
    """Create a temporary repo with given filename→content pairs."""
    for name, content in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def test_compute_fingerprint_returns_hex():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        fp = compute_fingerprint(repo)
    assert isinstance(fp, str) and len(fp) == 64


def test_compute_fingerprint_same_files_same_hash():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1", "b.py": "y = 2"})
        fp1 = compute_fingerprint(repo)
        fp2 = compute_fingerprint(repo)
    assert fp1 == fp2


def test_compute_fingerprint_changes_when_file_modified():
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        f = repo / "a.py"
        f.write_text("x = 1", encoding="utf-8")
        fp1 = compute_fingerprint(repo)
        # Force mtime change by sleeping briefly and rewriting
        time.sleep(0.01)
        f.write_text("x = 2", encoding="utf-8")
        # touch to ensure mtime_ns changes even on fast filesystems
        f.touch()
        fp2 = compute_fingerprint(repo)
    assert fp1 != fp2


def test_compute_fingerprint_ignores_noncoding_files():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        fp1 = compute_fingerprint(repo)
        (repo / "README.pdf").write_bytes(b"\xff")
        fp2 = compute_fingerprint(repo)
    assert fp1 == fp2


def test_compute_fingerprint_ignores_graphify_out():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        fp1 = compute_fingerprint(repo)
        out = repo / "graphify-out"
        out.mkdir()
        (out / "graph.json").write_text("{}", encoding="utf-8")
        fp2 = compute_fingerprint(repo)
    assert fp1 == fp2


def test_save_and_load_fingerprint_round_trip():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        (repo / "graphify-out").mkdir()
        saved_fp = save_fingerprint(repo)
        loaded = load_fingerprint(repo)
    assert loaded is not None
    assert loaded["fingerprint"] == saved_fp
    assert loaded["repo"] == str(repo)
    assert "built_at" in loaded
    assert "strategy" in loaded


def test_load_fingerprint_returns_none_if_absent():
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        result = load_fingerprint(repo)
    assert result is None


def test_check_staleness_fresh():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        (repo / "graphify-out").mkdir()
        save_fingerprint(repo)
        assert check_staleness(repo) == "FRESH"


def test_check_staleness_stale_after_file_change():
    with tempfile.TemporaryDirectory() as d:
        repo = _make_repo(Path(d), {"a.py": "x = 1"})
        (repo / "graphify-out").mkdir()
        save_fingerprint(repo)
        time.sleep(0.01)
        f = repo / "a.py"
        f.write_text("x = 999", encoding="utf-8")
        f.touch()
        assert check_staleness(repo) == "STALE"


def test_check_staleness_unknown_if_no_fingerprint():
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        assert check_staleness(repo) == "UNKNOWN"
