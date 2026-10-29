# Bobagraph — Prompt and Usage Log

This log records prompts and actions that actually occurred during development, using IBM Bob as the coding assistant. It separates skills used **to build the plugin** (development aids, not shipped) from instructions shipped **with the plugin** (the `bobagraph://usage` resource and README).

---

## Section 1 — Skills Used to BUILD the Plugin (Development Only)

These are personal skills from the `ported-workflows` library. They were used as development-process guidance and are **not shipped in the ZIP, not imported, and not referenced in any shipped file.**

| Skill | Purpose | Applied in session |
|---|---|---|
| `ponytail` | Keep changes minimal — only what was asked | Throughout implementation |
| `verification-before-completion` | Run and record actual test output before claiming complete | Before each phase closeout |
| `tdd` (via test-driven-development workflow) | Write tests before implementation for `change_brief` | Phase 3 implementation |
| `diagnosing-bugs` | Systematic failure investigation | When 5 isolated tests failed |

**How they were used:** Loaded in the Bob coding session via `use_skill`. They provided guidance on process and minimal-change discipline. No code from these skills was copied into the plugin.

---

## Section 2 — Instructions Shipped WITH the Plugin

The `bobagraph://usage` resource (in [`bobagraph/server.py`](../bobagraph/server.py)) is the runtime guidance Bob reads. It is self-contained, references no external skills, and covers:
- When to use each of the 11 tools
- Edge confidence interpretation (EXTRACTED / INFERRED / AMBIGUOUS)
- How to handle truncated results
- How to refresh a stale graph

The [`README.md`](../README.md) is the customer setup guide.

Neither references `ported-workflows` or any personal skill.

---

## Section 3 — Actual Prompts Submitted to Bob (Development Session)

These are the prompts submitted during the Bobathon development session. This was a multi-session Bob agent conversation. The session history is available as the chat context that produced this codebase.

### Planning and contract phase

**Prompt (session start):**
> "We are building a hackathon project: a standalone local Graphify-based integration for IBM Bob. [...] acknowledge this contract briefly. Do not build until the next planning prompt."

**Purpose:** Establish acceptance requirements and get acknowledgement before implementation.
**Workflow loaded by Bob:** None (acknowledgement only).
**Files changed:** None.
**Result:** Contract acknowledged. One open question identified (none material enough to block).

---

**Prompt (planning):**
> "Plan the Bobagraph implementation. Capability matrix, architecture, what we build vs upstream, test approach."

**Purpose:** Architecture decision before coding.
**Workflow loaded by Bob:** None at this stage; `ported-workflows` was available in environment.
**Files changed:** None (plan produced inline).
**Result:** Agreed scope: 10 upstream tools + 1 `change_brief` tool + `bobagraph://usage` resource + single setup command. Baseline-only delivery confirmed.

---

### Implementation phase

**Prompt:**
> "Build the example_repo with intentional features: duplicate symbols, indirect call chain, unrelated module. Extract the graph."

**Purpose:** Create a representative test codebase for demonstration and testing.
**Workflow loaded by Bob:** `ported-workflows` available.
**Files created:** `example_repo/api/handlers.py`, `example_repo/orders/service.py`, `example_repo/pricing/rules.py`, `example_repo/pricing/vouchers.py`, `example_repo/storage/models.py`, `example_repo/storage/repository.py`, `example_repo/notifications/sender.py`, plus test files (37 tests).
**Result:** Graph extracted: 160 nodes, 354 edges, 15 communities, 92% EXTRACTED / 8% INFERRED.

---

**Prompt:**
> "Implement change_brief.py TDD — tests first."

**Purpose:** Core original tool, test-driven.
**Workflow loaded by Bob:** `ported-workflows` (tdd workflow loaded as development aid).
**Files created:** `bobagraph/change_brief.py`, `bobagraph/tests/test_change_brief.py` (18 tests).
**Result:** 18 unit tests passing.

---

**Prompt:**
> "Implement server.py — MCP stdio server exposing change_brief and bobagraph://usage."

**Purpose:** Make the tool accessible to Bob via the MCP protocol.
**Files created:** `bobagraph/server.py`.
**Result:** Protocol-level server with path validation, traversal rejection, usage resource.

---

**Prompt:**
> "Implement bobagraph_setup.py — install, refresh, status, uninstall."

**Purpose:** Single-command distributable installer.
**Files created:** `bobagraph_setup.py`.
**Result:** Idempotent installer with mtime+size fingerprint staleness detection.

---

**Prompt:**
> "Write test_mcp_server.py — 18 MCP integration tests."

**Purpose:** Protocol-level validation independent of Bob UI.
**Files created:** `bobagraph/tests/test_mcp_server.py`.
**Result:** 18 integration tests covering initialize, tools/list, tools/call, resources, path validation.

---

**Prompt:**
> "Write test_fingerprint.py — 10 staleness tests."

**Purpose:** Verify FRESH/STALE/UNKNOWN detection logic.
**Files created:** `bobagraph/tests/test_fingerprint.py`.
**Result:** 10 tests passing.

---

### Verification and bug-fix phase

**Prompt:**
> "Run isolated verification: clean install in env -i with spaces in path."

**Purpose:** Check A — verify no developer paths leak, install works in unfamiliar directory.
**Workflow loaded by Bob:** `verification-before-completion` (loaded as development aid).
**Files changed:** `bobagraph/tests/test_change_brief.py` (added `_find_graph()` to handle non-standard install directory names), `bobagraph/tests/test_mcp_server.py` (same fix + `VENV_PYTHON = sys.executable`).
**Failures found and fixed:**
- `GRAPH_PATH` hardcoded to `example_repo/` — failed when directory had spaces
- `VENV_PYTHON = .venv/bin/python` — failed outside dev environment
- `test_path_traversal` — traversal check never reached because `GRAPH_PATH` was invalid first
**Result after fixes:** 46/46 in isolation.

---

**Prompt (this session):**
> "Package the implementation. Create: problem statement, ZIP, video script, usage log, feedback template, release checklist."

**Purpose:** Final delivery preparation.
**Workflow loaded by Bob:** `ported-workflows` (verification-before-completion).
**Files created:** `bobagraph-v0.1.0.zip`, `docs/problem-statement.md`, `docs/video-script.md`, `docs/usage-log.md` (this file), `docs/feedback-template.md`, `docs/release-checklist.md`.
**ZIP verification:** 46/46 tests from fresh unzip + install + `env -i` run. `.bob/mcp.json` contains no developer paths.

---

## Section 4 — What Was NOT Recorded

The following are **pending** — evidence does not exist yet:

| Item | Status |
|---|---|
| Bob UI conversation screenshots | **Pending** — no screenshots captured during Bob chat sessions |
| Bob UI demonstration without ported-workflows loaded | **Pending** — manual step not yet performed; isolated MCP protocol tests confirm the contract but are not a substitute |
| Exact timestamps of each prompt | **Pending** — session timestamps not extracted; dates shown in evidence files are file modification times |
| Verbatim reconstructed prompts | Several prompts above are reconstructed from memory/context, not copied verbatim from session logs. They represent the intent accurately; word-for-word fidelity is not guaranteed. |

---

## Section 5 — Evidence Files

| File | Contents |
|---|---|
| `evidence/build_evidence.txt` | graph_stats, query_graph, change_brief real tool call outputs |
| `evidence/setup_run.txt` | Full install command output, generated `.bob/mcp.json`, idempotent re-run, merge preservation test |
| `evidence/verification.txt` | Check A + Check B results (first pass) |
| `evidence/verification_pass2.txt` | 11-item verification checklist: all items passed |
