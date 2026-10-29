"""change_brief: given a list of changed files, produce a structured impact brief
from a graphify graph.json.

This is Bobagraph's original contribution — not part of the upstream graphify engine.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path


def _load_graph(graph_path: str) -> dict:
    """Load graph.json.  Raises ValueError on wrong extension, FileNotFoundError when missing."""
    p = Path(graph_path)
    if p.suffix != ".json":
        raise ValueError(f"graph_path must be a .json file, got: {graph_path!r}")
    if not p.exists():
        raise FileNotFoundError(f"Graph file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _nodes_for_files(graph: dict, files: list[str]) -> list[dict]:
    """Return all graph nodes whose source_file matches any entry in files."""
    if not files:
        return []
    file_set = set(files)
    return [n for n in graph.get("nodes", []) if n.get("source_file") in file_set]


def _degree_map(graph: dict) -> dict[str, int]:
    """Build a node-id → degree mapping from the link list."""
    deg: dict[str, int] = {}
    for link in graph.get("links", []):
        src = link.get("source") or link.get("_src")
        tgt = link.get("target") or link.get("_tgt")
        for nid in (src, tgt):
            if nid:
                deg[nid] = deg.get(nid, 0) + 1
    return deg


def build_brief(graph_path: str, changed_files: list[str]) -> dict:
    """Return a structured impact brief for the given changed files.

    Keys:
      changed_files      — echo of the input list
      affected_nodes     — count of graph nodes from those files
      communities_touched — sorted list of community ids/names touched
      high_degree_nodes  — top nodes by degree (label, source_file, degree), desc
      summary            — human-readable one-paragraph impact statement
    """
    graph = _load_graph(graph_path)
    nodes = _nodes_for_files(graph, changed_files)

    if not nodes:
        return {
            "changed_files": changed_files,
            "affected_nodes": 0,
            "communities_touched": [],
            "high_degree_nodes": [],
            "summary": (
                f"No graph nodes found for the given files. "
                f"The graph may need rebuilding, or the paths may not match stored source_file values. "
                f"Files provided: {changed_files}"
            ),
        }

    # Communities
    communities: list = sorted(
        {n.get("community") for n in nodes if n.get("community") is not None},
        key=lambda c: str(c),
    )

    # Top nodes by degree
    deg_map = _degree_map(graph)
    node_degrees = sorted(
        [
            {
                "label": n.get("label", n["id"]),
                "source_file": n.get("source_file", ""),
                "degree": deg_map.get(n["id"], 0),
            }
            for n in nodes
        ],
        key=lambda x: x["degree"],
        reverse=True,
    )
    top_nodes = node_degrees[:10]

    # Summary
    file_list = ", ".join(changed_files) if changed_files else "(none)"
    top_label = top_nodes[0]["label"] if top_nodes else "N/A"
    summary = (
        f"{len(nodes)} graph node(s) are defined in the changed file(s): {file_list}. "
        f"They touch {len(communities)} community/communities "
        f"({', '.join(str(c) for c in communities[:5])}{'...' if len(communities) > 5 else ''}). "
        f"The highest-degree affected node is '{top_label}' "
        f"(degree {top_nodes[0]['degree'] if top_nodes else 0}). "
        f"Review callers and importers of the top-degree nodes for ripple effects."
    )

    return {
        "changed_files": changed_files,
        "affected_nodes": len(nodes),
        "communities_touched": communities,
        "high_degree_nodes": top_nodes,
        "summary": summary,
    }
