"""MCP client integration test for bobagraph.server.

Tests the server through its actual stdio JSON-RPC protocol:
  - initialization handshake
  - tools/list (verify schema matches what we documented)
  - tools/call change_brief with a valid query
  - tools/call change_brief with an unknown/missing file
  - tools/call change_brief with malformed input (missing required field)
  - comparison of MCP response to direct build_brief() output

Stdout of the server must be clean JSON-RPC only (diagnostics on stderr).
We do NOT claim Bob connectivity — this is a standalone client test.
"""
import json
import subprocess
import sys
from pathlib import Path
import pytest


def _find_graph() -> str:
    """Locate graph.json relative to the distributable root.

    Searches for graphify-out/graph.json under:
      1. example_repo/   (dev checkout name)
      2. any sibling directory (post-install with spaces, renamed folder, etc.)
    Returns the first match found, or the canonical dev path (which will fail
    with FileNotFoundError if not built — test will report clearly).
    """
    dist_root = Path(__file__).parent.parent.parent
    candidate = dist_root / "example_repo" / "graphify-out" / "graph.json"
    if candidate.exists():
        return str(candidate)
    for sibling in sorted(dist_root.iterdir()):
        if sibling.is_dir() and sibling.name not in (
            "bobagraph", "bobagraph-env", ".venv", ".git", ".bob"
        ):
            g = sibling / "graphify-out" / "graph.json"
            if g.exists():
                return str(g)
    return str(candidate)  # return canonical path (will produce clear FileNotFoundError)


GRAPH_PATH = _find_graph()

# Use sys.executable so tests run with whatever Python launched pytest —
# works in dev .venv, bobagraph-env, or any isolated environment.
VENV_PYTHON = sys.executable
SERVER_MODULE = "bobagraph.server"


# ---------------------------------------------------------------------------
# Helper: send one JSON-RPC message, capture stdout line response
# ---------------------------------------------------------------------------

def _jsonrpc(method: str, params: dict, msg_id: int = 1) -> dict:
    """Send one JSON-RPC request to the server subprocess and return the response."""
    msg = json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
    proc = subprocess.run(
        [VENV_PYTHON, "-m", SERVER_MODULE],
        input=f'{{"jsonrpc":"2.0","id":0,"method":"initialize","params":{{}}}}\n'
              f'{{"jsonrpc":"2.0","method":"notifications/initialized","params":{{}}}}\n'
              f'{msg}\n',
        capture_output=True,
        text=True,
        timeout=10,
    )
    # stdout must be clean JSON lines only
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    # First line is the initialize response, second (if any notification was skipped) is ours
    # Find the response matching our msg_id
    for line in lines:
        try:
            obj = json.loads(line)
            if obj.get("id") == msg_id:
                return obj
        except json.JSONDecodeError:
            pass
    raise AssertionError(
        f"No response found for id={msg_id} in stdout.\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

def test_initialize_returns_server_info():
    proc = subprocess.run(
        [VENV_PYTHON, "-m", SERVER_MODULE],
        input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n',
        capture_output=True, text=True, timeout=10,
    )
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    assert len(lines) >= 1
    resp = json.loads(lines[0])
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "bobagraph"
    assert "tools" in resp["result"]["capabilities"]


def test_initialize_stdout_is_valid_json_only():
    """Ensure no diagnostic text leaks onto stdout."""
    proc = subprocess.run(
        [VENV_PYTHON, "-m", SERVER_MODULE],
        input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n',
        capture_output=True, text=True, timeout=10,
    )
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            json.loads(line)  # raises if not valid JSON


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------

def test_tools_list_contains_change_brief():
    resp = _jsonrpc("tools/list", {}, msg_id=2)
    tools = resp["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "change_brief" in names


def test_change_brief_schema_has_required_fields():
    resp = _jsonrpc("tools/list", {}, msg_id=2)
    tools = {t["name"]: t for t in resp["result"]["tools"]}
    schema = tools["change_brief"]["inputSchema"]
    assert "graph_path" in schema["properties"]
    assert "changed_files" in schema["properties"]
    assert set(schema["required"]) >= {"graph_path", "changed_files"}


# ---------------------------------------------------------------------------
# tools/call — valid input
# ---------------------------------------------------------------------------

def test_call_change_brief_valid_file():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": GRAPH_PATH,
            "changed_files": ["pricing/rules.py"],
        },
    }, msg_id=3)
    assert resp.get("error") is None
    content = resp["result"]["content"][0]["text"]
    brief = json.loads(content)
    assert brief["affected_nodes"] > 0
    assert brief["changed_files"] == ["pricing/rules.py"]
    assert isinstance(brief["communities_touched"], list)
    assert isinstance(brief["high_degree_nodes"], list)
    assert isinstance(brief["summary"], str)


def test_call_change_brief_multiple_files():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": GRAPH_PATH,
            "changed_files": ["pricing/rules.py", "orders/service.py"],
        },
    }, msg_id=4)
    assert resp.get("error") is None
    brief = json.loads(resp["result"]["content"][0]["text"])
    assert brief["affected_nodes"] > 0
    sources = {n["source_file"] for n in brief["high_degree_nodes"]}
    # At least one of our files should appear in the top nodes
    assert sources & {"pricing/rules.py", "orders/service.py"}


# ---------------------------------------------------------------------------
# tools/call — missing/unknown file
# ---------------------------------------------------------------------------

def test_call_change_brief_unknown_file_returns_zero_nodes():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": GRAPH_PATH,
            "changed_files": ["no/such/module.py"],
        },
    }, msg_id=5)
    brief = json.loads(resp["result"]["content"][0]["text"])
    assert brief["affected_nodes"] == 0
    assert brief["communities_touched"] == []


def test_call_change_brief_missing_graph_returns_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": "/nonexistent/graph.json",
            "changed_files": ["pricing/rules.py"],
        },
    }, msg_id=6)
    result = resp["result"]
    assert result["isError"] is True
    assert "not found" in result["content"][0]["text"].lower()


# ---------------------------------------------------------------------------
# tools/call — malformed input
# ---------------------------------------------------------------------------

def test_call_change_brief_missing_graph_path_is_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "changed_files": ["pricing/rules.py"],
            # graph_path intentionally omitted
        },
    }, msg_id=7)
    result = resp["result"]
    assert result["isError"] is True


def test_call_change_brief_changed_files_not_list_is_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": GRAPH_PATH,
            "changed_files": "not-a-list",
        },
    }, msg_id=8)
    result = resp["result"]
    assert result["isError"] is True


def test_call_unknown_tool_returns_error():
    resp = _jsonrpc("tools/call", {"name": "nonexistent_tool", "arguments": {}}, msg_id=9)
    result = resp["result"]
    assert result["isError"] is True


# ---------------------------------------------------------------------------
# Cross-check: MCP response == direct build_brief() call
# ---------------------------------------------------------------------------

def test_mcp_response_matches_direct_call():
    """The MCP server must return the same data as calling build_brief() directly."""
    from bobagraph.change_brief import build_brief
    files = ["pricing/rules.py", "orders/service.py"]
    direct = build_brief(GRAPH_PATH, files)

    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {"graph_path": GRAPH_PATH, "changed_files": files},
    }, msg_id=10)
    via_mcp = json.loads(resp["result"]["content"][0]["text"])

    assert via_mcp["changed_files"] == direct["changed_files"]
    assert via_mcp["affected_nodes"] == direct["affected_nodes"]
    assert via_mcp["communities_touched"] == direct["communities_touched"]
    assert via_mcp["high_degree_nodes"] == direct["high_degree_nodes"]
    assert via_mcp["summary"] == direct["summary"]


# ---------------------------------------------------------------------------
# resources/list and resources/read (added in server.py v2)
# ---------------------------------------------------------------------------

def test_resources_list_contains_usage():
    resp = _jsonrpc("resources/list", {}, msg_id=20)
    resources = resp["result"]["resources"]
    uris = [r["uri"] for r in resources]
    assert "bobagraph://usage" in uris


def test_resources_read_usage_returns_markdown():
    resp = _jsonrpc("resources/read", {"uri": "bobagraph://usage"}, msg_id=21)
    contents = resp["result"]["contents"]
    assert len(contents) == 1
    text = contents[0]["text"]
    assert "query_graph" in text
    assert "change_brief" in text
    assert "EXTRACTED" in text
    assert "INFERRED" in text
    assert "refresh" in text.lower()


def test_resources_read_unknown_uri_returns_error():
    resp = _jsonrpc("resources/read", {"uri": "bobagraph://doesnotexist"}, msg_id=22)
    assert "error" in resp


# ---------------------------------------------------------------------------
# Path validation tests
# ---------------------------------------------------------------------------

def test_relative_graph_path_returns_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {"graph_path": "relative/path/graph.json", "changed_files": []},
    }, msg_id=30)
    assert resp["result"]["isError"] is True
    assert "absolute" in resp["result"]["content"][0]["text"].lower()


def test_path_traversal_in_changed_files_returns_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": GRAPH_PATH,
            "changed_files": ["../../../etc/passwd"],
        },
    }, msg_id=31)
    assert resp["result"]["isError"] is True
    assert "traversal" in resp["result"]["content"][0]["text"].lower()


def test_nonjson_graph_path_returns_error():
    resp = _jsonrpc("tools/call", {
        "name": "change_brief",
        "arguments": {
            "graph_path": "/absolute/path/graph.txt",
            "changed_files": [],
        },
    }, msg_id=32)
    assert resp["result"]["isError"] is True

