"""Bobagraph MCP server — exposes the change_brief tool and usage guidance over stdio.

This is a thin MCP stdio server that adds one original Bobagraph tool
on top of the upstream graphify-mcp server (registered separately).

Tool: change_brief
  graph_path    Absolute path to graph.json
  changed_files List of source-relative file paths (e.g. from git diff --name-only)

Resource: bobagraph://usage
  Workflow guidance Bob reads at runtime — how to use the 11 available tools
  for architecture, dependency, and change-impact queries.

Stdout is kept clean for the MCP stdio protocol.
All diagnostic messages go to stderr.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

_USAGE_TEXT = """\
# Bobagraph + Graphify — query workflow

You have 11 tools: 10 from graphify (upstream) + 1 from bobagraph (change_brief).

## Architecture and dependency questions
Use query_graph(question="...") with mode="bfs" (default) for broad context.
Use mode="dfs" to trace a specific call or import path.
Start broad, then narrow with get_node or get_neighbors.

## Finding a symbol
Use get_node(label="SymbolName") — accepts the label shown in query results.
If the name is ambiguous (same label in multiple files), include the file:
  get_node(label="apply_discount()") returns the first match.
Use query_graph to surface both when a name is duplicated.

## Expanding connections
Use get_neighbors(label="SymbolName") to see all direct callers/callees/importers.
Use relation_filter="calls" or "imports" to narrow by edge type.
Use get_community(community_id=N) for all nodes in a subsystem.

## Directed paths and confidence
Use shortest_path(source="A", target="B") to trace how two concepts connect.
Edge confidence:
  EXTRACTED = explicit in source (import statement, direct call)
  INFERRED  = reasonable deduction (call-graph resolution, co-occurrence)
  AMBIGUOUS = uncertain — treat as a lead, verify in source
Direction: arc order is source → target even though graph.json stores directed:false
for rendering reasons.  Trust the arrow direction in tool output, not the flag.

## Source evidence
Every node in query results includes source_file and a line number (loc=L42).
Open that file at that line to verify the relationship or read the implementation.

## Change impact
Use change_brief(graph_path="...", changed_files=["path/relative/to/repo.py", ...])
Provide paths relative to the repository root, as from `git diff --name-only`.
The brief returns: affected_nodes count, communities touched, highest-degree nodes,
and a plain-English summary of ripple risk.

## Truncated results
The token_budget parameter on query_graph and get_neighbors (default 2000) controls
output size.  Increase it if results are cut off:
  query_graph(question="...", token_budget=4000)
god_nodes() top_n defaults to 10 — increase if you want more.

## Refreshing a stale graph
Run from a terminal:
  python bobagraph_setup.py refresh <repo_path>
Then ask Bob to reload MCP servers (Settings → MCP → Reload), or restart Bob.
Check freshness without rebuilding:
  python bobagraph_setup.py status <repo_path>
Staleness is detected by mtime+size fingerprint, not git HEAD.

## Unsupported inputs
Code files not yet indexed (new files, non-code types, files outside the scanned root)
will not appear in query results.  A change_brief on unindexed files returns
affected_nodes=0 and explains the situation in the summary field.
"""


def _validate_graph_path(graph_path: str) -> tuple[Path, str | None]:
    """Validate graph_path: must be an absolute .json file that exists.
    Returns (resolved_path, error_message_or_None).
    No file reads are performed here — only path validation.
    """
    if not graph_path:
        return Path("."), "graph_path is required"
    p = Path(graph_path)
    if not p.is_absolute():
        return p, f"graph_path must be absolute, got: {graph_path!r}"
    if p.suffix != ".json":
        return p, f"graph_path must end with .json, got: {graph_path!r}"
    resolved = p.resolve()
    if not resolved.exists():
        return resolved, f"Graph file not found: {resolved}"
    return resolved, None


def _validate_changed_files(changed_files: object) -> tuple[list[str], str | None]:
    """Validate changed_files is a list of non-empty strings. Returns (list, error)."""
    if not isinstance(changed_files, list):
        return [], "changed_files must be an array of strings"
    cleaned: list[str] = []
    for item in changed_files:
        if not isinstance(item, str):
            return [], f"each entry in changed_files must be a string, got: {type(item).__name__}"
        s = item.strip()
        # Reject path traversal attempts
        if ".." in Path(s).parts:
            return [], f"path traversal not allowed in changed_files entry: {item!r}"
        cleaned.append(s)
    return cleaned, None


def _tool_description() -> str:
    return (
        "Analyze the change impact of a set of modified source files against a "
        "Bobagraph/Graphify knowledge graph. "
        "Use when the user asks: 'what is the impact of these changes?', "
        "'which parts of the codebase do these files touch?', or "
        "'what should I review after changing X?'. "
        "Pass the absolute path to graph.json and a list of changed file paths "
        "relative to the scanned repository root "
        "(e.g. from `git diff --name-only`). "
        "Returns: affected_nodes (count), communities_touched (list of community ids), "
        "high_degree_nodes (top affected nodes by connection count, descending), "
        "and a human-readable summary of ripple risk. "
        "Limitation: only covers files already in graph.json — "
        "rebuild after source changes with `python bobagraph_setup.py refresh <repo>`."
    )


def _handle_initialize(msg_id, params):
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "bobagraph", "version": "0.1.0"},
            "capabilities": {"tools": {}, "resources": {}},
        },
    }


def _handle_tools_list(msg_id):
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "tools": [
                {
                    "name": "change_brief",
                    "description": _tool_description(),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "graph_path": {
                                "type": "string",
                                "description": (
                                    "Absolute path to graph.json "
                                    "(e.g. /home/user/repo/graphify-out/graph.json)"
                                ),
                            },
                            "changed_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Source files relative to the repository root as stored "
                                    "in the graph (e.g. ['orders/service.py', 'pricing/rules.py']). "
                                    "Obtain from `git diff --name-only` or similar."
                                ),
                            },
                        },
                        "required": ["graph_path", "changed_files"],
                    },
                }
            ]
        },
    }


def _handle_resources_list(msg_id):
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "resources": [
                {
                    "uri": "bobagraph://usage",
                    "name": "Bobagraph Usage Guide",
                    "description": (
                        "Workflow guidance for architecture, dependency, change-impact, "
                        "path/confidence interpretation, source evidence, and graph refresh. "
                        "Read this to understand how to use all 11 available tools effectively."
                    ),
                    "mimeType": "text/markdown",
                }
            ]
        },
    }


def _handle_resources_read(msg_id, params):
    uri = str((params or {}).get("uri", ""))
    if uri == "bobagraph://usage":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "contents": [
                    {
                        "uri": "bobagraph://usage",
                        "mimeType": "text/markdown",
                        "text": _USAGE_TEXT,
                    }
                ]
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32602, "message": f"Unknown resource: {uri}"},
    }


def _handle_tools_call(msg_id, params):
    from bobagraph.change_brief import build_brief

    name = params.get("name", "")
    if name != "change_brief":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            },
        }

    args = params.get("arguments") or {}
    graph_path_raw = args.get("graph_path", "")
    changed_files_raw = args.get("changed_files", [])

    # Validate graph_path
    resolved_path, path_err = _validate_graph_path(graph_path_raw)
    if path_err:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": path_err}], "isError": True},
        }

    # Validate changed_files
    cleaned_files, files_err = _validate_changed_files(changed_files_raw)
    if files_err:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": files_err}], "isError": True},
        }

    try:
        brief = build_brief(str(resolved_path), cleaned_files)
        text = json.dumps(brief, indent=2)
    except FileNotFoundError as exc:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": f"Graph not found: {exc}"}], "isError": True},
        }
    except ValueError as exc:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": f"Invalid input: {exc}"}], "isError": True},
        }
    except Exception as exc:
        print(f"[bobagraph] change_brief error: {exc}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": f"Internal error: {exc}"}], "isError": True},
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {"content": [{"type": "text", "text": text}], "isError": False},
    }


def _dispatch(msg: dict) -> dict | None:
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _handle_initialize(msg_id, params)
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _handle_tools_list(msg_id)
    if method == "tools/call":
        return _handle_tools_call(msg_id, params)
    if method == "resources/list":
        return _handle_resources_list(msg_id)
    if method == "resources/read":
        return _handle_resources_read(msg_id, params)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main() -> None:
    """Run the MCP stdio server loop. Stdout is reserved for JSON-RPC only."""
    print("[bobagraph] server starting", file=sys.stderr)
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            print(json.dumps(resp), flush=True)
            continue
        try:
            response = _dispatch(msg)
        except Exception as exc:
            print(f"[bobagraph] dispatch error: {exc}", file=sys.stderr)
            response = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {"code": -32603, "message": "Internal error"},
            }
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
