# Bobagraph — Release Checklist

Last updated: 2026-10-29

---

## Code and Tests

| Check | Status | Evidence |
|---|---|---|
| 46 bobagraph tests pass (dev environment) | ✅ PASSED | `evidence/verification_pass2.txt` item 1: 83 passed |
| 46 bobagraph tests pass in isolation (`env -i`, path with spaces) | ✅ PASSED | This session: 46/46 from isolated `/tmp` run |
| 46 bobagraph tests pass from fresh ZIP unzip + install | ✅ PASSED | This session: 46/46 from `/tmp/bobagraph-zip-verify` |
| 37 example_repo tests pass | ✅ PASSED | `evidence/verification_pass2.txt` item 1: 83 total (37 + 46) |
| No personal skill paths in any shipped file | ✅ PASSED | `evidence/verification_pass2.txt` item 11; grep scan this session |
| Stdout of MCP server is clean JSON only | ✅ PASSED | `evidence/verification_pass2.txt` item 10 |
| Path traversal blocked in changed_files | ✅ PASSED | `evidence/verification_pass2.txt` item 4 |
| Relative graph_path rejected with clear message | ✅ PASSED | `evidence/verification_pass2.txt` item 5 |
| Malformed `.bob/mcp.json` rejected (not silently replaced) | ✅ PASSED | `evidence/verification_pass2.txt` item 3 |

---

## Setup and Configuration

| Check | Status | Evidence |
|---|---|---|
| `install` command works from ZIP in fresh directory | ✅ PASSED | This session: `/tmp/bobagraph-zip-verify` install log |
| Generated `.bob/mcp.json` uses recipient paths (no developer paths) | ✅ PASSED | This session: grep check on `/tmp/bobagraph-zip-verify/.bob/mcp.json` |
| `GRAPHIFY_BACKEND=none` and `GRAPHIFY_QUERY_LOG_DISABLE=1` set | ✅ PASSED | `evidence/setup_run.txt`, `evidence/verification_pass2.txt` item 7 |
| Existing `.bob/mcp.json` entries and `alwaysAllow` preserved on re-run | ✅ PASSED | `evidence/setup_run.txt` merge preservation test |
| `uninstall` removes only our entries, preserves others | ✅ PASSED | `evidence/verification_pass2.txt` item 8 |
| Idempotent re-install after uninstall | ✅ PASSED | `evidence/verification_pass2.txt` item 9 |
| `status` command shows FRESH / STALE / UNKNOWN correctly | ✅ PASSED | `evidence/setup_run.txt`, `evidence/verification_pass2.txt` item 2 |

---

## Data Correctness

| Check | Status | Evidence |
|---|---|---|
| `shortest_path` result matches direct CLI output | ✅ PASSED | `evidence/verification.txt` Check B |
| Source evidence verified: `handlers.py L4` = import statement | ✅ PASSED | `evidence/verification.txt` Check B |
| Duplicate symbols returned as separate nodes | ✅ PASSED | `evidence/verification.txt` Check B |
| Absent symbol returns clear message (not crash) | ✅ PASSED | `evidence/verification.txt` Check B |
| Missing graph returns `isError: True` with message | ✅ PASSED | test_mcp_server.py test passing |
| STALE detection: edit file → STALE → refresh → FRESH | ✅ PASSED | `evidence/verification.txt` Check B |
| `change_brief` for unrelated module returns 0 cross-community nodes | ✅ PASSED | `evidence/verification.txt` Check B |
| `high_degree_nodes` sorted descending by degree | ✅ PASSED | `evidence/verification.txt` Check B |

---

## Deliverables

| Deliverable | Status | Path |
|---|---|---|
| Source ZIP | ✅ CREATED | `bobagraph-v0.1.0.zip` (32 files, 88 KB) |
| Problem statement | ✅ CREATED | `docs/problem-statement.md` |
| Video script | ✅ CREATED | `docs/video-script.md` |
| Usage / prompt log | ✅ CREATED | `docs/usage-log.md` |
| Individual feedback template | ✅ CREATED | `docs/feedback-template.md` |
| Release checklist | ✅ CREATED | `docs/release-checklist.md` (this file) |

---

## Attribution and Licensing

| Check | Status |
|---|---|
| Upstream graphify credited (Apache 2.0, author, URL) | ✅ PASSED |
| `NOTICE` file present and correct | ✅ PASSED |
| `LICENSE` (Apache 2.0) present | ✅ PASSED |
| README attribution section correct | ✅ PASSED |
| No claim to be a Graphify Cloud clone | ✅ PASSED |
| `graph.html` network dependency documented | ✅ PASSED (README community labels section + problem-statement) |

---

## Pending — Requires Human Action

| Item | Who | Status |
|---|---|---|
| **Video recording** | Team | ⏳ PENDING — script written at `docs/video-script.md`; not yet recorded |
| **Bob UI demonstration without ported-workflows** | Any team member | ⏳ PENDING — manually rename `~/.bob/skills/ported-workflows`, open Bob, run a `query_graph` call, screenshot result; do not mark passed until done |
| **Individual feedback forms** | Each team member | ⏳ PENDING — template at `docs/feedback-template.md`; each person fills their own |
| **Submission** | Team | ⏳ PENDING — not submitted |

---

## Known Limitations (Documented, Not Bugs)

| Limitation | Where Documented |
|---|---|
| `graph.html` requires network access (loads vis-network from unpkg.com) | README "Visual graph" section; problem-statement |
| Community labels are `Community N` in code-only mode (LLM disabled) | README "Community labels" section; video script Scene 6 |
| `change_brief` reports nodes *defined in* changed files, not callers | README; tool description; usage resource; problem-statement |
| Bob's own usage and source-processing settings still apply | README Prerequisites; problem-statement |
| Installation requires network access (PyPI + GitHub) | README Prerequisites table |

---

## Shortest Next Action

1. **Record the video** using `docs/video-script.md`. Open a terminal in `/tmp/bobagraph-zip-verify` (already installed) for the install/test scenes.
2. **Run Bob UI demo**: rename `~/.bob/skills/ported-workflows` → `~/.bob/skills/ported-workflows.bak`, open Bob in the zip-verify directory (which has `.bob/mcp.json`), run one `query_graph` call, screenshot, rename back.
3. **Each team member fills `docs/feedback-template.md`** (copy to a named file, e.g. `docs/feedback-alice.md`).
4. **Submit** using the hackathon submission form.
