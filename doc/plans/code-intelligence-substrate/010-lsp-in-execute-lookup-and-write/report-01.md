# Run report — 010-lsp-in-execute-lookup-and-write (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/lsp-execute-lookup-write-43d0ar` (harness-assigned; kept as-is per lane contract)    **PR:** _pending_    **Outcome:** in progress

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

_(filled in at Step 8 from actual check state)_

## Reviewer participation

_(filled in at Step 8 from stored comment bodies; expected population from the automatic-review registry: `coderabbitai`, `cuioss-review-bot`, `sourcery-ai`)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at Step 9)_

## What have we learned (Step 9)

_(filled in at Step 9)_

## Residue

_(filled in at close)_
