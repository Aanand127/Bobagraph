# Bobagraph

Connect **IBM Bob** to any local repository using the [Graphify](https://github.com/Graphify-Labs/graphify) knowledge-graph engine. One command installs everything, indexes the code, and writes Bob's MCP configuration — no cloud account, no API key.

---

## Prerequisites

| Requirement | Minimum | Check |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| pip | any | `python3 -m pip --version` |
| Network | initial install only (PyPI + GitHub) | — |

To run the included tests (optional):
```bash
bobagraph-env/bin/pip install pytest
bobagraph-env/bin/python -m pytest bobagraph/tests/
```

No Graphify Cloud account. No LLM API key. Bob's own source-processing and usage settings still apply when Bob calls the tools.

---

## Install

```bash
python3 bobagraph_setup.py install /path/to/your/repo
```

What this does:
1. Creates `bobagraph-env/` (isolated virtual environment).
2. Installs `graphifyy[mcp]` pinned to a tested commit.
3. Indexes your repository code with tree-sitter AST — no LLM, nothing leaves your machine.
4. Writes `.bob/mcp.json` — adds only the `graphify` and `bobagraph` server entries; all other entries and `alwaysAllow` settings are preserved.

> **Paths with spaces or Unicode** are handled safely — no shell interpolation.

---

## Connect Bob

1. Open Bob in the Bobagraph directory (where `.bob/mcp.json` was written).
2. **Settings → MCP tab** — Bob should auto-detect the config file.
3. If the servers don't appear: click **Reload MCP Servers**.
4. You'll see two servers: `graphify` (10 tools) and `bobagraph` (1 tool + 1 resource).

---

## Query examples

```
# Architecture overview
"What are the most connected modules in this codebase?"
→ Use god_nodes or: query_graph question="most connected modules"

# Dependency chain
"How does OrderAPI connect to calculate_item_price?"
→ shortest_path source="OrderAPI" target="calculate_item_price"

# Direct callers
"What calls apply_discount?"
→ get_neighbors label="apply_discount()" relation_filter="calls"

# Change impact
"What is the impact of changing pricing/rules.py and orders/service.py?"
→ change_brief graph_path="<graph.json path>" changed_files=["pricing/rules.py","orders/service.py"]

# Inspect a node
"Show me everything about OrderService"
→ get_node label="OrderService"

# Read workflow guidance
→ Read resource: bobagraph://usage
```

---

## Refresh after code changes

```bash
python3 bobagraph_setup.py refresh /path/to/your/repo
```

Then in Bob: **Settings → MCP → Reload MCP Servers** (or restart Bob).

---

## Check graph status

```bash
python3 bobagraph_setup.py status /path/to/your/repo
```

Reports: repository identity, graph size, node/edge counts, build timestamp, fingerprint, and staleness (`FRESH` / `STALE` / `UNKNOWN`).

**Staleness detection**: uses mtime+size fingerprint over all source files — does not rely on git HEAD, which would miss uncommitted edits.

---

## Uninstall

```bash
python3 bobagraph_setup.py uninstall
```

Removes only the `graphify` and `bobagraph` entries from `.bob/mcp.json`. Removes `bobagraph-env/`. Never touches your source repository or unrelated Bob settings.

---

## Understand results

### Edge confidence
| Label | Meaning |
|---|---|
| `EXTRACTED` | Explicit in source (import, direct call) |
| `INFERRED` | Reasonable deduction — verify before trusting |
| `AMBIGUOUS` | Uncertain — treat as a lead |

### Edge direction
`shortest_path` and `query_graph` show arc direction as `-->` or `<--`. Trust the arrow. `graph.json` stores `directed: false` for visualization reasons only.

### Truncated results
If output is cut off, increase `token_budget`:
```
query_graph question="..." token_budget=4000
```

### Unsupported inputs
Files not in the last graph build (new files, non-code types) return no nodes. Run `refresh` after adding files.

---

## Community labels

Community names appear as `Community N` in code-only mode. This is expected — label generation requires an LLM backend, which is disabled by default. The community ID numbers in query results are still useful for `get_community(community_id=N)`.

---

## Visual graph

```bash
open example_repo/graphify-out/graph.html   # macOS
xdg-open example_repo/graphify-out/graph.html  # Linux
```

---

## Troubleshoot

| Problem | Fix |
|---|---|
| Tools not in Bob | Settings → MCP → Reload MCP Servers |
| `bobagraph-env` not found | Re-run `install` |
| `change_brief` returns 0 nodes | Run `refresh` — file may be new since last build |
| Staleness = UNKNOWN | Run `refresh` to create a fingerprint |
| `.bob/mcp.json` malformed | Fix JSON manually, then re-run `install` |
| Community names are `Community N` | Expected in code-only mode; IDs still work |

---

## Attribution

Bobagraph uses the [graphify](https://github.com/Graphify-Labs/graphify) engine (Apache 2.0, © 2026 Safi Shamsi and contributors). The graph engine, `graphify-mcp` server (10 tools), AST extraction, and `graph.html` visualizer are upstream works. Bobagraph is community-built and is not affiliated with or endorsed by Graphify Labs.

Bobagraph's original code: [`bobagraph/change_brief.py`](bobagraph/change_brief.py), [`bobagraph/server.py`](bobagraph/server.py), [`bobagraph_setup.py`](bobagraph_setup.py). See [NOTICE](NOTICE) and [LICENSE](LICENSE).
