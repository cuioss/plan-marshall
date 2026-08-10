# Run report — 010-lsp-in-execute-lookup-and-write (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/lsp-execute-lookup-write-43d0ar` (harness-assigned; kept as-is per lane contract)    **PR:** [#1140](https://github.com/cuioss/plan-marshall/pull/1140)    **Outcome:** completed (all deliverables landed on the branch, verified; auto-merge armed — see Merge gate)

## Skills loaded

Loaded by reading the bundle source path (the plugin was not assumed present in this cloud session):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `cloud-plan-lane` (the working contract, loaded first)

Conditional loads deferred until code is written (persona-implementer, python-core, pytest-testing, plugin-architecture, ref-asciidoc read on demand). Recorded per the contract; none was unobtainable.

## D0 — GATE (settled against a live server, not documentation)

**Outcome: CONFIRMED.** A real language server — `pyright-langserver` 1.1.408 (installed at `/root/.local/bin`, via `uv` tools) — was driven over LSP/JSON-RPC (stdio) by a stdlib-only client. No hand-built stand-in was substituted (the plan forbids that on refutation; it is equally avoided on confirmation).

Measurement (workspace scoped to the `manage-architecture` module — a representative task working set):

| Operation | Latency | Result |
|---|---|---|
| Cold start (`initialize`) | **413.4 ms** | server ready |
| `workspace/symbol` (query "run") | 240.6 ms | 0 (pyright needs indexing enabled / config-pull answered — handled in the real client) |
| first `publishDiagnostics` | 736.3 ms | 5 diagnostics |
| `textDocument/documentSymbol` | **2.7 ms** | 10 symbols (coordinates, no bodies) |
| `textDocument/references` | **11.9 ms** | 3 locations |
| `textDocument/definition` | **2.6 ms** | 1 location |
| `textDocument/rename` → `WorkspaceEdit` | **4.9 ms** | **multi-file edit spanning 2 files** |

The rename produced a real, parser-verified, **multi-file `WorkspaceEdit` in under 5 ms** — D2's central primitive, verified against a real server. Diagnostics are available in under a second — D3's primitive. Coordinate lookups are single-digit-to-low-tens of milliseconds.

**Premise refuted?** No. The standing objection (per-query server boot is not viable for one-shot subprocesses) is answered by the measurement: cold start is ~0.4 s, so the natural amortization unit is a **per-call batch** (a single script invocation that boots the server, runs a batch of lookups and/or an edit+re-diagnose, and tears down).

### Hosting decision (D0's second half)

**Decision: host the server _inside the envelope_ — a short-lived subprocess of the client script (per call), not a daemon and not a socket-exposed sidecar.**

Rationale:
- Cold start ~0.4 s makes per-call boot cheap; the value is in the per-call latencies (2–12 ms) and the multi-file `WorkspaceEdit`, not in cross-turn warmth.
- Avoids widening `marshalld`'s machine-global trust boundary. The build-server map shows `marshalld` is one-op-per-connection request/reply — a poor structural fit for a long-lived stateful LSP session — and the plan flags an LSP holding an open workspace as "a new class of long-lived child" whose adoption into the daemon would be an explicit, high-risk recorded decision. Hosting per-call sidesteps that entirely.
- Avoids the unestablished risk (claim label) that a dispatched leaf can hold or reach a long-lived process across turns: a per-call subprocess lives and dies inside one `Bash`→script call, which the leaf tool surface trivially supports.
- Matches the shipped build-skill shape (spawn a subprocess, suspend the LLM, return one TOON; cost independent of duration / file count) — the same shape the plan's OBSERVED token-management claim names.

## Split decision (the split guard)

**Decision: proceed UNSPLIT (D0+D1+D2+D3+D4 in one PR).**

Rationale: the in-envelope host decision collapses D1 (read) and D2 (write) onto one shared client core (spawn → initialize → request), so a lookup/write split would fork the same scaffolding across two PRs and duplicate the config-surface review. D2 is a thin, high-value addition over D1 (rename → capture footprint → apply → re-diagnose), and its adversarial test is cheap to include alongside the read side.

## Deliverables

Commits: `6a96ab0` (mechanics + config + tests), `f5ae40f` (docs + consumer wiring). Plan-dir + D0 record in `e4154aa`.

- **D0 — GATE (CONFIRMED).** Measured against a live `pyright-langserver` (see the D0 section above). Hosting decision recorded: in-envelope per-call subprocess. Verification: a real measurement exists; the premise is not refuted. Split decision recorded (unsplit).
- **D1 — read side.** `lsp_client.py` `lookup` verb (`definition` / `references` / `document-symbol` / `workspace-symbol`) returns coordinates without reading file bodies (`_run_lookup`). Coverage contract: `state` + `provider_count` keep `not_configured` / `unreachable` / `ok`-found-nothing separately representable. Verified: `test_lsp_client.py::test_three_states_are_distinguishable` (negative control) + real-server `test_lsp_integration.py::test_real_document_symbol_and_references` / `test_real_workspace_symbol_after_indexing`.
- **D2 — write side.** `edit` verb: `rename` → `WorkspaceEdit` → footprint captured from the edit (`_lsp_workspace_edit.capture_footprint`) → applied (`apply_workspace_edit`) → diagnostics re-run → worsened set fails and rolls back (`edit_verdict` + `restore_files`). Verified adversarially: `test_lsp_client.py::test_edit_worsened_fails_and_rolls_back` and real-server `test_lsp_integration.py::test_real_adversarial_defect_fails_and_rolls_back` (a deliberate defect through the WorkspaceEdit path makes the parser's re-diagnose fail the step). Footprint-matches-edit asserted by `test_capture_footprint_from_edit` / `test_apply_and_restore_round_trip`.
- **D3 — diagnostics pre-build signal.** `diagnose` verb + `DIAGNOSTICS_BOUNDARY_NOTE` in every payload; boundary prose in `lsp-client/SKILL.md` and the user page. Cold read dispatched to the Step-6 sub-agent.
- **D4 — opt-in config + no-op degradation + docs.** Machine-local `language_servers` section (new `manage-run-config` `language-server` get/set/list/remove verbs); `lsp_client` reads it and degrades to `read_edit` when `not_configured`/`unreachable`; unconfigured is byte-identical (the leaf never invokes the server). Distinguishability asserted by `test_preflight_not_configured` vs `test_preflight_unreachable`. Docs: `doc/user/lsp-code-intelligence.adoc`, `run-config-standard.md` § Language-Servers, execute-task consumer seams.

⚠ **Bundle edits owe a local `/sync-plugin-cache`** (this lane cannot run it — `target/`/`~/.claude/` are absent/off-limits). Recorded so whoever picks the work up locally syncs the cache.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (lsp-client scripts, run_config.py, tests) → full `./pw verify` required and run.

**Result: SUCCESS.** `./pw verify` (whole tree): quality-gate (mypy: no issues in 385 files; ruff: all checks passed; SPDX: passed; plugin-doctor: `status: pass`, `total_issues: 0` across all 31 rules incl. `scan_manage_invocation`, `analyze_skill_mode`, `analyze_sys_path_bootstrap`, `broken-relative-link`), test-compile (mypy over tests: clean), module-tests: **18714 passed, 14 skipped** (the 14 are pre-existing environment guards; the 4 lsp-client real-pyright integration tests RAN and passed here because pyright is installed).

## Findings

### Pre-PR verification sub-agent (Step 6)

The sub-agent re-ran the real-pyright suite (present in this session) and verdicted D0–D4 all **SATISFIED**, both mandated cold reads **passing**:

- **Cold read D3 (diagnostics boundary):** read as *"supplements the quality gate"* — driven by "a clean `diagnose` is *not* a green build. Always run the canonical build … before treating a change as correct." **Pass.**
- **Cold read D4 (opt-in page):** read as *"you lose nothing if you don't configure it"* — driven by "*This is strictly opt-in, and an unconfigured project loses nothing.*" **Pass.**

**Finding 1 (real, FIXED):** `cmd_preflight` returned `state: 'ok'` for the reachable case, but both consumer surfaces (`execute-task/SKILL.md`, `lsp-client/SKILL.md` Scripts table) tell a leaf to gate on `state: ready` — a state the code never emitted, so a leaf following the wiring would never match a reachable server and wrongly fall back. The reachable-preflight path was also untested. Fixed in `d46769e`: `cmd_preflight` now emits `STATE_READY` ('ready') for the reachable case (the preflight precondition sentinel, distinct from a run verb's `ok`), the `ready`/`ok` distinction is documented, and `test_real_preflight_ready` was added. Re-verified by a focused second sub-agent: original finding **resolved**, no new inconsistency, `35 passed` in the lsp-client suite.

**Observation A (not a gap, no change):** the real-server adversarial test exercises the apply→re-diagnose→verdict helpers inline; the `_run_edit` orchestration's fail/rollback branch is covered separately by `test_edit_worsened_fails_and_rolls_back` (fake transport). Together they satisfy D2's adversarial requirement.

**Observation B (rejected as not-a-defect):** the module docstring's "an unconfigured project never reaches this script" was slightly overstated (a leaf may call a run verb without a preflight guard and get a `degraded` no-op). Outcome is still byte-identical (no mutation, no server contact), so D4's done-condition holds; the wording was tightened in `d46769e` for precision rather than treated as a behavioural defect.

### CI

Read from actual check state (`pull_request_read get_check_runs`): after the first push, `verify / conclusion` = **success**, `verify / verify` = success, `review / review` = success, `verify / gate` = success, `dependency-review` = success, `generate-check` = success (`auto-merge` and `Sourcery review` checks = skipped). Two further commits followed (the review-fix `9dc172d` and this report), which re-trigger `verify`; the merge queue re-verifies the final head before landing.

**Finding 2 (real, FIXED — from `cuioss-review-bot`):** `_lsp_jsonrpc._read_loop` wrapped its whole loop in `try/except (OSError, ValueError)`, so one malformed frame (a stray stdout line, a bad `Content-Length`, or a length-0 body making `json.loads('')` raise) killed the reader thread permanently and hung every later request until its 30s timeout. Fixed in `9dc172d`: per-message resilience (skip a bad/length-0 frame, keep reading; only EOF/broken-pipe ends the loop), plus `test_lsp_transport.py` driving a fake server that emits a length-0 junk frame before the real response (CI-portable, no pyright). Replied on the thread.

## Reviewer participation

Expected population derived from the automatic-review registry `author_login` fields (`automatic-review/standards/{coderabbit,pr-agent,sourcery}.md`; cross-named in `.github/workflows/pr-agent.yml`). Verdicts from the stored comment bodies:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" over the diff: "PR contains tests", "No security concerns identified", and one actionable finding ("Unhandled Exception in Read Loop") — Finding 2 above, fixed. |
| `coderabbitai` | `rate-limited` | Published only a quota notice: "Review limit reached … you've reached your PR review limit … Next review available in 37 minutes." Engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published only a quota notice: "you have reached your weekly rate limit of 500000 diff characters." |

**Coverage: 1 of 3 reviewed.** § Step 8 shortfall disclosure fired: stated to the operator as "Review coverage 1 of 3 — `cuioss-review-bot` reviewed (its one finding fixed); `coderabbitai` rate-limited (resets in ~37 min); `sourcery-ai` rate-limited (weekly quota)." Per the contract this is a **disclosure, not a block** — rate limits are routine and outside our control, so the merge is not held on them.

(A non-reviewer `cla-assistant` comment reported CLA status `not_signed`; it is an operator/account concern, not a code-review finding, and is not among this repo's required merge checks.)

## Cost

- **Tokens:** not available to the agent in this session — this interactive Claude Code cloud session does not surface its own token accounting to the agent, so no figure is stated rather than a guessed one.
- **Wall-clock:** ~1.5 h of session time end to end (recon → D0 measurement → implementation → verify → PR → review cycle), read from the run's own tool activity; the PR was opened at 2026-08-10 15:20 UTC.
- **Population:** whatever the above would count is this single interactive cloud session. ⛔ It is **not comparable** to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary this session does not share. The figures are therefore reported without a comparison.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — core skills + conditional (persona-implementer, python-core, pytest-testing, plugin-architecture, ref-asciidoc read on demand); named above. GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/*`, kept as-is. |
| 2 Branch on origin | Done — branch pushed on arrival (was absent) and after every commit. |
| 3 Plan directory | Done — `…/010-lsp-in-execute-lookup-and-write/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed. |
| 4 Per-commit gate | Done — every source-touching commit was preceded by a clean `quality-gate` (mypy/ruff/SPDX/plugin-doctor `total_issues: 0`). |
| 4 Pushed | Done — no unpushed commit (this report is the final pre-merge commit). |
| 5 Build gate | Done — `*.py` changed → full `./pw verify` = SUCCESS (18714 passed, 14 pre-existing skips). |
| 6 Verification sub-agent | Done — one finding (preflight `ready`/`ok`), fixed and re-verified; both cold reads passed. |
| 7 PR cycle | Done — PR #1140; every comment dispositioned (§ Reviewer participation). |
| 8 Merge gate | Auto-merge armed (squash); the merge queue enforces green on the final head. **MERGED not confirmable within this session** — the queue lands asynchronously after CI, and this session cannot self-wake (the `send_later` / `subscribe_pr_activity` MCP tools are approval-gated here). The orchestrator collects the landing from the PR merge event. |
| 8 Bridge | Nothing under `doc/plans/` outside this plan's own directory was changed; this report carries the PR number and per-deliverable outcome. |
| 9 This check | Appended here. |

⚠ **Sync owed:** the plan edited `marketplace/bundles/**`, so a local `/sync-plugin-cache` is owed (this lane cannot run it).

## What have we learned (Step 9)

**GAP (operator-confirmed): the `cloud-plan-lane` skill should ALLOW this completion path.**

Evidence from this run: Step 8's merge gate is written as a synchronous drive — "verify all checks green, then merge, then confirm `state: MERGED`." That assumes the run can *wait* for CI and reviewers and *re-check* across the review cycle. In this Claude Code cloud session the self-wake mechanisms the wait depends on — the `send_later` and `subscribe_pr_activity` MCP tools — were **approval-gated** (both returned "requires approval"), and Bash cannot poll GitHub (no `gh`, no API auth; the GitHub MCP server is the only path). The run therefore could **not** autonomously block-until-green and confirm the terminal `MERGED` state within the session.

The run adapted by arming auto-merge (the merge queue enforces the green gate structurally — it will not land a red head) and disclosing that the final landing is confirmed by the orchestrator at collect, from the PR merge event, rather than within the session.

**The gap:** the contract does not currently sanction this. It should. Arming auto-merge and handing the `MERGED` confirmation to the collect step is a **legitimate completion, not a partial run**, whenever the self-wake tools are unavailable — and the skill should say so explicitly at Step 8, so a future run in the same environment does not read its own inability to self-confirm as a failure. Per Step 9 this is **not** self-approved and does **not** ship inside this plan's PR; the operator has confirmed the gap, and the amendment ships as a separate `chore/` PR touching only the `cloud-plan-lane` skill (and `doc/plans/README.md` if it restates the gate).

## Residue

- **MERGED confirmation:** auto-merge is armed on PR #1140; the queue lands it once the final head's CI is green. Confirm `state: MERGED` from the PR merge event (orchestrator collect, or an operator check).
- **Local plugin-cache sync** owed for the `marketplace/bundles/**` edits.
- **Reviewer coverage** was 1 of 3 (two bots rate-limited); a later re-review is possible once quotas reset but is not required for the merge.
