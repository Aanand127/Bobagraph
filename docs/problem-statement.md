# Bobagraph — Problem Statement and Solution

## The Problem

IBM Bob can read and edit code files, but it has no persistent structured understanding of how a codebase is connected. Every question about architecture, dependencies, or the blast radius of a change is answered by Bob re-reading files from scratch. For a 10-file project that is fast enough. For a 200-file production codebase it means repeated, expensive file reads and answers that miss indirect relationships Bob never traced.

There is no built-in way to ask Bob: "What modules call `apply_discount()`?" or "If I change `pricing/rules.py` and `orders/service.py`, what else is affected?" without Bob reading large portions of the codebase every time.

## The Solution

Bobagraph connects IBM Bob to a pre-built, local knowledge graph of the repository. One setup command indexes the code with tree-sitter AST extraction — no LLM, nothing leaves the machine. The resulting graph is served to Bob via two MCP servers, giving Bob 11 graph-query tools available in every conversation.

```
python3 bobagraph_setup.py install /path/to/repo
```

That command:
1. Creates an isolated Python virtual environment (`bobagraph-env/`)
2. Installs `graphifyy[mcp]` pinned to a tested upstream commit
3. Runs code-only AST extraction → `graphify-out/graph.json` (160 nodes, 354 edges on the example repo)
4. Writes `.bob/mcp.json` with recipient-local paths; preserves all existing entries

Bob then has instant structured access to the graph — no file re-reading required for graph questions.

## What Each Part Does

### Upstream: Graphify (Apache 2.0 — not our code)

The [graphify](https://github.com/Graphify-Labs/graphify) open-source project provides:
- **AST extraction engine** — 40-language tree-sitter parser that extracts nodes (functions, classes, imports) and edges (calls, imports) into `graph.json`
- **`graphify-mcp` server** — exposes 10 MCP tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`, `list_prs`, `get_pr_impact`, `triage_prs`
- **`graph.html`** — interactive vis-network visualization (requires network access to load vis-network from unpkg.com)
- **Community detection** — Louvain algorithm groups nodes into subsystems

We pin to commit `0a8cd4e1e342235fe53e881fb5d591bf0460071f` (v0.9.97) for reproducibility.

### Our Original Contribution: Bobagraph

We built three original files on top of the upstream engine:

**[`bobagraph/change_brief.py`](../bobagraph/change_brief.py)** — Change impact analysis. Given a list of source files (e.g. from `git diff --name-only`) and a `graph.json`, it returns:
- `affected_nodes` — count of graph nodes defined in the changed files
- `communities_touched` — which subsystems those nodes belong to
- `high_degree_nodes` — the most-connected affected nodes (sorted by degree, descending) — these are the highest-risk ripple points
- `summary` — a plain-English sentence describing the scope

**[`bobagraph/server.py`](../bobagraph/server.py)** — A second MCP stdio server that exposes `change_brief` as Bob tool #11, plus a `bobagraph://usage` resource containing workflow guidance Bob can read at runtime. Includes path validation (absolute paths required, path traversal rejected).

**[`bobagraph_setup.py`](../bobagraph_setup.py)** — The single-command installer. Four subcommands: `install`, `refresh`, `status`, `uninstall`. Detects staleness using mtime+size fingerprint (not git HEAD — catches uncommitted edits). Merges `.bob/mcp.json` non-destructively.

## What We Explicitly Do Not Claim

- **Not a Graphify Cloud clone.** Graphify Cloud adds LLM-powered community labelling and enhanced query routing. We run with `GRAPHIFY_BACKEND=none` — community labels appear as `Community N` placeholders. The graph structure, edges, and all 10 query tools work fully.
- **Not fully offline.** Installation downloads packages from PyPI/GitHub. `graph.html` loads vis-network from `unpkg.com` — it will not render without network access. The MCP tools and `change_brief` are fully local after install.
- **No separate LLM API key required for Bobagraph itself.** Bob's own LLM usage and source-processing settings still apply when Bob calls the tools.
- **`change_brief` reports defined-in nodes, not callers.** It identifies nodes defined in the changed files. Callers and importers of those nodes are discoverable via `get_neighbors` — the summary explicitly names this next step.

## User Benefit

A developer with Bobagraph installed can ask Bob:

> "What is the impact of changing pricing/rules.py and orders/service.py?"

Bob calls `change_brief`, gets: 28 nodes affected, 5 communities touched, highest-risk node is `OrderService` (degree 21). Bob then names the review priorities — in one tool call, with no file reading.

> "How does OrderAPI connect to calculate_item_price?"

Bob calls `shortest_path` and gets the exact call chain with source file and line number for each hop — verified against the actual source.

This reduces the cost and latency of architectural reasoning in Bob conversations, especially on medium-to-large codebases where exhaustive file reading is impractical.
