# Bobagraph — Five-Minute Video Script

All scenes are based on real, working features. Every command and output shown was actually executed and recorded in `evidence/`.

---

## Scene 1 — The Problem (0:00–0:40)

**[Screen: a Bob chat window with a large Python repo open]**

**Narration:**
"IBM Bob is a great coding assistant. But ask it how modules are connected — or what breaks if you change this file — and it has to read every relevant file from scratch, every time.

For small projects, that's fine. For a real codebase, it's slow, expensive, and it misses indirect relationships Bob never followed.

We built Bobagraph: one setup command connects Bob to a pre-built, local knowledge graph of your repository. No cloud account. No API key. Just structured answers, instantly."

---

## Scene 2 — Install and Connect Overview (0:40–1:20)

**[Screen: terminal in the unzipped Bobagraph directory]**

**Narration:**
"Unzip the package. One command:"

**[Type and run:]**
```
python3 bobagraph_setup.py install example_repo
```

**[Show output scrolling — highlight key lines:]**
```
[bobagraph] Creating virtual environment at ./bobagraph-env …
[bobagraph] Installing graphifyy[mcp] (pinned) …
AST extraction on 19 code files...
wrote graph.json: 160 nodes, 354 edges, 15 communities
[bobagraph] Graph built: .../example_repo/graphify-out/graph.json
[bobagraph] Wrote .bob/mcp.json
```

**Narration:**
"That installed the upstream Graphify engine, extracted the AST graph — no LLM, nothing left the machine — and wrote Bob's MCP configuration with paths for this machine.

Now open Bob in this directory. Go to Settings → MCP. You'll see two servers: `graphify` with 10 tools, and `bobagraph` with 1 tool and a usage guide resource."

**[Show Bob's MCP settings panel with both servers listed]**

---

## Scene 3 — Real Source-Backed Graph Question (1:20–2:40)

**[Screen: Bob chat window]**

**Narration:**
"Let's ask a real architectural question about the example repository — a small e-commerce order processing system."

**[Type in Bob:]**
```
How does the API layer connect to calculate_item_price? 
Use shortest_path to show the call chain.
```

**[Bob calls `shortest_path`, show the response:]**
```
shortest_path source="OrderAPI" target="calculate_item_price()"

OrderAPI [api/handlers.py L4] --> OrderService [orders/service.py L8] 
  --> apply_discount() [pricing/rules.py L30]
  --> calculate_item_price() [pricing/rules.py L42]
```

**Narration:**
"Bob traced the exact path — with source file and line number at each hop. Let's verify one of those claims."

**[Open `api/handlers.py` at line 4, show:]**
```python
from orders.service import OrderService
```

**Narration:**
"Confirmed: `api/handlers.py` line 4 is exactly that import. The graph edge is `EXTRACTED` — meaning it came directly from a tree-sitter parse of the source, not inference."

**[Type in Bob:]**
```
What are the most connected nodes in this codebase?
```

**[Bob calls `god_nodes`, show the top result:]**
```
1. OrderService — degree 21 (orders/service.py L8)
2. apply_discount() — degree 12 (pricing/rules.py L30)
```

**Narration:**
"`OrderService` is the hub of this codebase — degree 21, meaning 21 direct connections. Anything touching it has high ripple risk."

---

## Scene 4 — Our Original Contribution: Change Brief (2:40–3:40)

**[Screen: Bob chat window]**

**Narration:**
"The upstream Graphify engine gives us 10 query tools. We added an 11th: `change_brief`. It's purpose-built for code review — tell it which files changed and it returns a structured impact report."

**[Type in Bob:]**
```
I'm about to change pricing/rules.py and orders/service.py.
Run change_brief to assess the impact.
```

**[Bob calls `change_brief` with graph_path and changed_files, show the response:]**
```json
{
  "affected_nodes": 28,
  "communities_touched": [0, 1, 2, 3, 4],
  "high_degree_nodes": [
    {"label": "OrderService", "source_file": "orders/service.py", "degree": 21},
    {"label": "apply_discount()", "source_file": "pricing/rules.py", "degree": 12}
  ],
  "summary": "28 graph node(s) are defined in the changed file(s)... The highest-degree affected node is 'OrderService' (degree 21). Review callers and importers of the top-degree nodes for ripple effects."
}
```

**Narration:**
"28 nodes defined in those files. 5 communities — meaning these changes touch most of the codebase's subsystems. The highest-risk node is `OrderService` with 21 connections.

One important scope note: `change_brief` reports nodes *defined in* the changed files. To find what *calls* those nodes — the callers — use `get_neighbors`. The summary says exactly that."

---

## Scene 5 — Clean Installation Evidence + Tests (3:40–4:30)

**[Screen: terminal — the ZIP verify environment]**

**Narration:**
"We verified the package in a clean environment — no developer files, no personal skills. Let me show the evidence."

**[Show:]**
```bash
# Unzip to fresh /tmp directory
unzip bobagraph-v0.1.0.zip -d /tmp/bobagraph-verify
ls /tmp/bobagraph-verify
```
```
LICENSE  NOTICE  README.md  bobagraph  bobagraph_setup.py  
example_repo  pyproject.toml  requirements.lock.txt
```

**Narration:**
"No `bobagraph-env`, no `.bob/mcp.json`, no `__pycache__`, no `graphify-out`. Clean source. After install:"

**[Show the generated `.bob/mcp.json` — highlight paths pointing to `/tmp/...`]**

**Narration:**
"Paths point to the recipient's machine — not the developer's."

**[Run tests:]**
```bash
# Install pytest, run isolated suite
python -m pytest bobagraph/tests/ -v
```
```
46 passed in 0.64s
```

**Narration:**
"46 tests: 18 unit tests for `change_brief`, 10 for the fingerprint/staleness logic, 18 MCP integration tests that talk to the server through the actual JSON-RPC protocol.

The Bob UI demonstration — loading Bob with `ported-workflows` unavailable — is **pending**. The MCP protocol tests confirm the full tool contract is correct. The Bob UI step requires a manual screen recording."

---

## Scene 6 — Development Context, Attribution, Limits (4:30–5:00)

**[Screen: split — `NOTICE` file + `README.md` troubleshoot section]**

**Narration:**
"Bobagraph is built on the open-source Graphify project — Apache 2.0, credited in our NOTICE file. The graph engine, the 10 MCP tools, the AST extraction, the `graph.html` visualizer — all upstream work.

Our original contribution is `change_brief.py`, `server.py`, and `bobagraph_setup.py`.

A few honest limits: the `graph.html` visual viewer loads vis-network from unpkg.com — it needs network access to render. The MCP tools are fully local. Community labels appear as `Community N` in code-only mode — label generation needs an LLM backend, which we deliberately disable. And Bob's own usage settings apply when Bob calls the tools.

Bobagraph is a hackathon project. The setup is one command. The code is readable. It works."

---

## Production Notes

- Record at 1080p, terminal font ≥ 14pt, dark background for contrast
- Show real terminal output — do not fake or speed up
- Scene 3 source verification is the strongest evidence moment — linger on it
- Scene 5: do NOT show the Bob UI demo as passed unless you have actually opened Bob without ported-workflows loaded and executed a query; mark it pending if not
- Total run time target: 4:45–5:00
