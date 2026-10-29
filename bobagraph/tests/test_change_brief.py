"""Tests for bobagraph.change_brief — written BEFORE implementation (TDD)."""
import json
import os
import pytest
from pathlib import Path

from bobagraph.change_brief import build_brief, _load_graph, _nodes_for_files


def _find_graph() -> str:
    """Locate graph.json relative to the distributable root.

    Searches for graphify-out/graph.json under:
      1. example_repo/   (dev checkout name)
      2. any sibling directory (post-install with spaces, renamed folder, etc.)
    Returns the first match found, or the canonical dev path (which will fail
    with FileNotFoundError if not built — test will skip or report clearly).
    """
    dist_root = Path(__file__).parent.parent.parent
    # Try canonical dev name first
    candidate = dist_root / "example_repo" / "graphify-out" / "graph.json"
    if candidate.exists():
        return str(candidate)
    # Walk siblings for any graphify-out/graph.json
    for sibling in sorted(dist_root.iterdir()):
        if sibling.is_dir() and sibling.name not in ("bobagraph", "bobagraph-env", ".venv", ".git", ".bob"):
            g = sibling / "graphify-out" / "graph.json"
            if g.exists():
                return str(g)
    return str(candidate)  # return canonical (will fail if not built)


GRAPH_PATH = _find_graph()


# ---------------------------------------------------------------------------
# _load_graph
# ---------------------------------------------------------------------------

def test_load_graph_returns_dict():
    g = _load_graph(GRAPH_PATH)
    assert isinstance(g, dict)
    assert "nodes" in g
    assert "links" in g


def test_load_graph_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        _load_graph("/nonexistent/graph.json")


def test_load_graph_wrong_extension_raises():
    with pytest.raises(ValueError):
        _load_graph("/tmp/graph.txt")


# ---------------------------------------------------------------------------
# _nodes_for_files
# ---------------------------------------------------------------------------

def test_nodes_for_files_matches_by_source_file():
    g = _load_graph(GRAPH_PATH)
    matched = _nodes_for_files(g, ["pricing/rules.py"])
    assert len(matched) > 0
    # Every returned node should reference pricing/rules.py
    for node in matched:
        assert node.get("source_file") == "pricing/rules.py"


def test_nodes_for_files_empty_list_returns_empty():
    g = _load_graph(GRAPH_PATH)
    assert _nodes_for_files(g, []) == []


def test_nodes_for_files_unknown_file_returns_empty():
    g = _load_graph(GRAPH_PATH)
    assert _nodes_for_files(g, ["does/not/exist.py"]) == []


def test_nodes_for_files_multiple_files():
    g = _load_graph(GRAPH_PATH)
    matched = _nodes_for_files(g, ["pricing/rules.py", "orders/service.py"])
    sources = {n["source_file"] for n in matched}
    assert "pricing/rules.py" in sources
    assert "orders/service.py" in sources


# ---------------------------------------------------------------------------
# build_brief
# ---------------------------------------------------------------------------

def test_build_brief_returns_dict():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    assert isinstance(result, dict)


def test_build_brief_has_required_keys():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    for key in ("changed_files", "affected_nodes", "communities_touched", "high_degree_nodes", "summary"):
        assert key in result, f"missing key: {key}"


def test_build_brief_changed_files_echoed():
    files = ["pricing/rules.py", "orders/service.py"]
    result = build_brief(GRAPH_PATH, files)
    assert result["changed_files"] == files


def test_build_brief_affected_nodes_nonempty_for_known_file():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    assert result["affected_nodes"] > 0


def test_build_brief_zero_nodes_for_unknown_file():
    result = build_brief(GRAPH_PATH, ["no/such/file.py"])
    assert result["affected_nodes"] == 0


def test_build_brief_communities_touched_is_list():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    assert isinstance(result["communities_touched"], list)


def test_build_brief_high_degree_nodes_is_list():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    assert isinstance(result["high_degree_nodes"], list)


def test_build_brief_summary_is_nonempty_string():
    result = build_brief(GRAPH_PATH, ["pricing/rules.py"])
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_build_brief_empty_files_list():
    result = build_brief(GRAPH_PATH, [])
    assert result["affected_nodes"] == 0
    assert result["communities_touched"] == []
    assert result["high_degree_nodes"] == []


def test_build_brief_summary_mentions_file():
    result = build_brief(GRAPH_PATH, ["orders/service.py"])
    assert "orders/service.py" in result["summary"]


def test_build_brief_high_degree_nodes_sorted_desc():
    result = build_brief(GRAPH_PATH, ["api/handlers.py", "orders/service.py", "pricing/rules.py"])
    degrees = [n["degree"] for n in result["high_degree_nodes"]]
    assert degrees == sorted(degrees, reverse=True)
