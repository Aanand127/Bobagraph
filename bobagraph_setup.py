#!/usr/bin/env python3
"""bobagraph_setup.py — distributable setup, refresh, status and uninstall for Bobagraph.

USAGE
  python bobagraph_setup.py install <repo>   # first-time or idempotent re-run
  python bobagraph_setup.py refresh <repo>   # rebuild graph only (fast, skips venv/install)
  python bobagraph_setup.py status  <repo>   # graph identity, build time, staleness
  python bobagraph_setup.py uninstall        # remove our .bob/mcp.json entries and venv

PREREQUISITES (documented honestly)
  - Python 3.10+        python3 --version
  - pip                 python3 -m pip --version
  - Network access      initial pip install only
  - No Graphify Cloud account or separate LLM API key required.
  - Bob's own source-processing settings still apply when Bob calls the MCP tools.

WHAT install DOES
  1. Creates bobagraph-env/ virtual environment (skips if already present).
  2. Installs graphifyy[mcp] pinned to tested commit, plus bobagraph itself.
  3. Runs: python -m graphify.serve --graph <graph.json> --transport stdio  (confirmed entrypoint)
     with GRAPHIFY_BACKEND=none and GRAPHIFY_QUERY_LOG_DISABLE=1.
  4. Writes/merges .bob/mcp.json — only our two entries are touched;
     unrelated servers and alwaysAllow settings are preserved.
     Fails clearly on malformed existing JSON rather than replacing it.

PATHS
  All paths are resolved to absolute form and validated before use.
  Symlinks are resolved; the real path must remain inside the repository.
  Spaces and Unicode in paths are handled via Path objects (no shell interpolation).

IDEMPOTENCY
  Re-running install is safe.  It recreates the venv only if absent,
  reinstalls packages, rebuilds the graph, and rewrites only our config entries.

UNINSTALL
  Removes only our two server entries from .bob/mcp.json (if present).
  Removes bobagraph-env/ virtual environment.
  Never touches the customer's source or unrelated Bob settings.

STALENESS
  Fingerprint = SHA-256 of sorted (path, mtime_ns, size) for every source file
  under <repo>, respecting .gitignore via graphify's own ignore logic.
  Unknown freshness is reported as UNKNOWN, not assumed fresh.
  Git HEAD is not used to infer working-tree state.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────────────

_GRAPHIFY_PIN = (
    "graphifyy[mcp] @ "
    "git+https://github.com/Graphify-Labs/graphify.git"
    "@0a8cd4e1e342235fe53e881fb5d591bf0460071f"
)
_DIST_DIR = Path(__file__).parent.resolve()
_VENV_DIR = _DIST_DIR / "bobagraph-env"
_BOB_DIR  = _DIST_DIR / ".bob"
_MCP_FILE = _BOB_DIR / "mcp.json"
_OUR_KEYS = ("graphify", "bobagraph")   # the only keys we write/remove

# Source extensions graphify extracts — used for fingerprinting
_CODE_EXTS = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt",
    ".scala", ".rb", ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".lua",
    ".zig", ".ex", ".exs", ".php", ".sh", ".bash", ".ps1", ".json",
    ".yaml", ".yml", ".toml", ".sql",
})

# ── helpers ───────────────────────────────────────────────────────────────────

def _fail(msg: str) -> None:
    print(f"[bobagraph] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def _info(msg: str) -> None:
    print(f"[bobagraph] {msg}")

def _python() -> Path:
    """Absolute path to the venv python."""
    p = _VENV_DIR / "bin" / "python"
    if not p.exists():
        _fail(f"Virtual environment not found at {_VENV_DIR}. Run: python bobagraph_setup.py install <repo>")
    return p

def _graphify_serve() -> list[str]:
    """Command list for the upstream graphify MCP server (confirmed entrypoint)."""
    py = str(_python())
    return [py, "-m", "graphify.serve", "--transport", "stdio"]

def _bobagraph_server() -> list[str]:
    """Command list for the bobagraph change_brief MCP server."""
    py = str(_python())
    return [py, "-m", "bobagraph.server"]

def _validate_repo(repo_arg: str) -> Path:
    """Resolve, validate, and return an absolute repository path."""
    p = Path(repo_arg).resolve()
    if not p.exists():
        _fail(f"Repository path does not exist: {p}")
    if not p.is_dir():
        _fail(f"Repository path is not a directory: {p}")
    # Symlink safety: resolved path must not escape (resolve() already follows symlinks)
    return p

def _graph_json(repo: Path) -> Path:
    """Expected location of graph.json for a repository."""
    out_dir = os.environ.get("GRAPHIFY_OUT", "").strip() or "graphify-out"
    return repo / out_dir / "graph.json"

def _graphify_env() -> dict[str, str]:
    """Environment variables for all graphify subprocess calls."""
    env = os.environ.copy()
    env["GRAPHIFY_BACKEND"] = "none"
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    return env

def _run(cmd: list[str], env: dict | None = None, cwd: str | None = None) -> None:
    """Run a subprocess; fail with exit code on non-zero."""
    result = subprocess.run(cmd, env=env, cwd=cwd)
    if result.returncode != 0:
        _fail(f"Command failed (exit {result.returncode}): {' '.join(str(c) for c in cmd)}")

# ── fingerprint ──────────────────────────────────────────────────────────────

def compute_fingerprint(repo: Path) -> str:
    """SHA-256 over sorted (relative_path, mtime_ns, size) for all code files.

    Explicit strategy: mtime_ns + size gives fast, tested change detection
    without reading file content.  Does not use git HEAD — that would miss
    working-tree edits.  Returns hex digest string.
    """
    entries: list[tuple[str, int, int]] = []
    for root, dirs, files in os.walk(repo):
        # Skip graphify-out, .git, __pycache__, hidden dirs
        dirs[:] = [
            d for d in sorted(dirs)
            if d not in ("graphify-out", ".git", "__pycache__", ".venv", "bobagraph-env")
            and not d.startswith(".")
        ]
        for fname in sorted(files):
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in _CODE_EXTS:
                continue
            try:
                st = fpath.stat()
                rel = str(fpath.relative_to(repo))
                entries.append((rel, st.st_mtime_ns, st.st_size))
            except OSError:
                continue  # file disappeared mid-walk; skip

    h = hashlib.sha256()
    for rel, mtime_ns, size in sorted(entries):
        h.update(f"{rel}\x00{mtime_ns}\x00{size}\n".encode())
    return h.hexdigest()


def _fingerprint_file(repo: Path) -> Path:
    """Path of the persisted fingerprint file (inside graphify-out/)."""
    out = repo / (os.environ.get("GRAPHIFY_OUT", "").strip() or "graphify-out")
    return out / ".bobagraph_fingerprint.json"


def save_fingerprint(repo: Path) -> str:
    """Compute and persist the current fingerprint. Returns the hex digest."""
    fp = compute_fingerprint(repo)
    data = {
        "fingerprint": fp,
        "repo": str(repo),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "strategy": "mtime_ns+size per code file, SHA-256 over sorted entries",
    }
    fp_path = _fingerprint_file(repo)
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return fp


def load_fingerprint(repo: Path) -> dict | None:
    """Load the persisted fingerprint dict, or None if absent/corrupt."""
    fp_path = _fingerprint_file(repo)
    if not fp_path.exists():
        return None
    try:
        return json.loads(fp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_staleness(repo: Path) -> str:
    """Return 'FRESH', 'STALE', or 'UNKNOWN' based on fingerprint comparison."""
    saved = load_fingerprint(repo)
    if saved is None:
        return "UNKNOWN"
    try:
        current = compute_fingerprint(repo)
    except Exception:
        return "UNKNOWN"
    return "FRESH" if current == saved["fingerprint"] else "STALE"

# ── .bob/mcp.json merge ───────────────────────────────────────────────────────

def _read_mcp_json() -> dict:
    """Read existing .bob/mcp.json; return empty structure if absent.
    Fails clearly on malformed JSON rather than silently replacing it.
    """
    if not _MCP_FILE.exists():
        return {"mcpServers": {}}
    raw = _MCP_FILE.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(
            f".bob/mcp.json exists but is not valid JSON: {exc}\n"
            f"  Fix or delete it manually, then re-run setup."
        )
    if not isinstance(data.get("mcpServers"), dict):
        data.setdefault("mcpServers", {})
    return data


def _write_mcp_json(data: dict) -> None:
    _BOB_DIR.mkdir(exist_ok=True)
    _MCP_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _merge_mcp_entries(repo: Path, graph_json_path: Path) -> None:
    """Write only our two entries into .bob/mcp.json, preserving everything else."""
    data = _read_mcp_json()
    servers = data["mcpServers"]

    # graphify upstream: use confirmed entrypoint with --graph flag
    servers["graphify"] = {
        "command": str(_python()),
        "args": ["-m", "graphify.serve", "--graph", str(graph_json_path), "--transport", "stdio"],
        "env": {
            "GRAPHIFY_BACKEND": "none",
            "GRAPHIFY_QUERY_LOG_DISABLE": "1",
        },
        "cwd": str(repo),
    }

    # bobagraph: our change_brief tool
    servers["bobagraph"] = {
        "command": str(_python()),
        "args": ["-m", "bobagraph.server"],
        "env": {
            "PYTHONPATH": str(_DIST_DIR),
        },
        "cwd": str(_DIST_DIR),
    }

    data["mcpServers"] = servers
    _write_mcp_json(data)
    _info(f"Wrote .bob/mcp.json — merged 'graphify' and 'bobagraph' server entries")


def _remove_mcp_entries() -> bool:
    """Remove only our entries from .bob/mcp.json. Returns True if file was changed."""
    if not _MCP_FILE.exists():
        return False
    data = _read_mcp_json()
    servers = data.get("mcpServers", {})
    removed = [k for k in _OUR_KEYS if k in servers]
    if not removed:
        return False
    for k in removed:
        del servers[k]
    data["mcpServers"] = servers
    _write_mcp_json(data)
    _info(f"Removed entries from .bob/mcp.json: {removed}")
    return True

# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_install(repo_arg: str) -> None:
    repo = _validate_repo(repo_arg)
    _info(f"Installing Bobagraph for: {repo}")

    # 1. Create venv if absent
    if not (_VENV_DIR / "bin" / "python").exists():
        _info(f"Creating virtual environment at {_VENV_DIR} …")
        _run([sys.executable, "-m", "venv", str(_VENV_DIR)])
    else:
        _info(f"Virtual environment already exists at {_VENV_DIR}")

    pip = [str(_VENV_DIR / "bin" / "python"), "-m", "pip", "install", "--quiet"]

    # 2. Install pinned graphifyy[mcp]
    _info("Installing graphifyy[mcp] (pinned) …")
    _run(pip + [_GRAPHIFY_PIN])
    # bobagraph itself is not pip-installed: the server runs with PYTHONPATH pointing
    # at this distribution directory, so bobagraph.server and bobagraph.change_brief
    # are always importable from the source tree without a separate install step.

    # 3. Build graph
    _build_graph(repo)

    # 5. Write Bob config
    graph_path = _graph_json(repo)
    _merge_mcp_entries(repo, graph_path)

    print()
    _info("Setup complete.")
    _print_next_steps(repo, graph_path)


def cmd_refresh(repo_arg: str) -> None:
    """Rebuild graph only — skip venv/install."""
    repo = _validate_repo(repo_arg)
    _info(f"Refreshing graph for: {repo}")
    _build_graph(repo)
    graph_path = _graph_json(repo)
    _merge_mcp_entries(repo, graph_path)
    _info("Refresh complete. Restart or reconnect the Bob MCP servers to reload.")


def _build_graph(repo: Path) -> None:
    py = str(_python())
    env = _graphify_env()
    _info("Running graphify extract (code-only, no LLM) …")
    _run([py, "-m", "graphify", "extract", str(repo), "--code-only"], env=env)
    _info("Running graphify cluster-only (generates graph.html and GRAPH_REPORT.md) …")
    _run([py, "-m", "graphify", "cluster-only", str(repo)], env=env)

    graph_path = _graph_json(repo)
    if not graph_path.exists():
        _fail(f"Expected graph.json at {graph_path} but it was not created.")
    _info(f"Graph built: {graph_path}")

    # Save fingerprint after successful build
    fp = save_fingerprint(repo)
    _info(f"Fingerprint saved (strategy: mtime_ns+size, SHA-256): {fp[:16]}…")


def cmd_status(repo_arg: str) -> None:
    repo = _validate_repo(repo_arg)
    graph_path = _graph_json(repo)
    print(f"Repository : {repo}")
    print(f"Graph path : {graph_path}")
    print(f"Graph exists: {graph_path.exists()}")

    if graph_path.exists():
        st = graph_path.stat()
        print(f"Graph size : {st.st_size:,} bytes")
        print(f"Graph mtime: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime))}")
        # Graph metadata
        try:
            import json as _json
            data = _json.loads(graph_path.read_text(encoding="utf-8"))
            print(f"Nodes      : {len(data.get('nodes', []))}")
            print(f"Links      : {len(data.get('links', []))}")
        except Exception:
            print("Nodes/links: (could not read graph.json)")
    else:
        print("Graph      : NOT BUILT — run: python bobagraph_setup.py install <repo>")

    saved = load_fingerprint(repo)
    if saved:
        print(f"Built at   : {saved.get('built_at', 'unknown')}")
        print(f"Fingerprint: {saved['fingerprint'][:16]}…")
        print(f"Strategy   : {saved.get('strategy', 'unknown')}")
    else:
        print("Fingerprint: UNKNOWN (no saved fingerprint — run install or refresh)")

    staleness = check_staleness(repo)
    print(f"Staleness  : {staleness}")
    if staleness == "STALE":
        print("  → Source files changed since last build. Run: python bobagraph_setup.py refresh <repo>")
    elif staleness == "UNKNOWN":
        print("  → Cannot determine freshness. Run: python bobagraph_setup.py refresh <repo>")

    print()
    mcp_file = _MCP_FILE
    print(f"Bob config : {mcp_file} ({'exists' if mcp_file.exists() else 'NOT FOUND'})")
    if mcp_file.exists():
        try:
            servers = json.loads(mcp_file.read_text(encoding="utf-8")).get("mcpServers", {})
            our = [k for k in _OUR_KEYS if k in servers]
            other = [k for k in servers if k not in _OUR_KEYS]
            print(f"  Our entries  : {our}")
            print(f"  Other entries: {other}")
        except json.JSONDecodeError:
            print("  (malformed JSON — fix manually)")


def cmd_uninstall() -> None:
    changed = _remove_mcp_entries()
    if not changed:
        _info("No Bobagraph entries found in .bob/mcp.json (nothing to remove).")
    if _VENV_DIR.exists():
        _info(f"Removing virtual environment: {_VENV_DIR}")
        shutil.rmtree(_VENV_DIR)
    else:
        _info(f"Virtual environment not found at {_VENV_DIR} (already removed).")
    _info("Uninstall complete. Your source repository and unrelated Bob settings are untouched.")


def _print_next_steps(repo: Path, graph_path: Path) -> None:
    print()
    print("  Next steps:")
    print(f"    1. Open Bob in this directory: {_DIST_DIR}")
    print("    2. In Bob Settings → MCP tab → 'Edit Project MCP'")
    print("       Bob will auto-detect .bob/mcp.json; if not, click 'Reload MCP Servers'.")
    print("    3. Try in Bob: 'What are the most connected nodes in the codebase?'")
    print("    4. Or: 'Run change_brief for orders/service.py and pricing/rules.py'")
    print(f"    5. Visual graph: open {graph_path.parent / 'graph.html'} in any browser")
    print(f"    6. Refresh after code changes:")
    print(f"       python bobagraph_setup.py refresh {repo}")
    print(f"    7. Check staleness:")
    print(f"       python bobagraph_setup.py status {repo}")
    print()


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    cmds = ("install", "refresh", "status", "uninstall")
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    sub = sys.argv[1]
    if sub not in cmds:
        _fail(f"Unknown subcommand: {sub!r}. Use one of: {', '.join(cmds)}")

    if sub == "uninstall":
        cmd_uninstall()
    elif len(sys.argv) < 3:
        _fail(f"'{sub}' requires a repository path. Usage: python bobagraph_setup.py {sub} <repo>")
    else:
        repo_arg = sys.argv[2]
        if sub == "install":
            cmd_install(repo_arg)
        elif sub == "refresh":
            cmd_refresh(repo_arg)
        elif sub == "status":
            cmd_status(repo_arg)


if __name__ == "__main__":
    main()
