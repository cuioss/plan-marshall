# Run report — 110-blocking-boundary-arms-on-a-call-not-a-state (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/blocking-boundary-arms-call-jqwzo9` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, via `Skill:`) — the working contract.
- `plan-marshall:ref-code-quality` — read from bundle path (always).
- `pm-plugin-development:plugin-script-architecture` — read from bundle path (always).
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned `claude/*`**, kept as-is per the contract.

## Deliverables

### D1 — GATE: establish the population (mutates nothing)

**Corpus reachability:** the archived-plan corpus lives under a machine-local, git-ignored path
**not present in this clone**. Per the plan's explicit instruction, it was **not searched for**. The
population counts ("how many archived plans carry no finalize-phase handshake row; how many of those
merged with pending actionable findings") are therefore **not derivable from the clone** and are
reported **blocked on corpus access**.

**Source-side derivation (decisive on its own).** The plan states the corpus question is settleable in
the clone: if **no call site emits a finalize-phase capture at all**, the row's absence is structural
and universal. That derivation was performed:

- `plan-marshall/workflow/execution.md` — at the `5-execute → 6-finalize` boundary emits only
  `phase_handshake capture --phase 5-execute` (execute-completion, lines ~415 and ~543 direct-entry),
  **never** `--phase 6-finalize`. The transition `manage-status transition --completed 5-execute`
  inlines `cmd_verify(phase=5-execute)` — drift-only; `_capture_pending_findings_blocking_count`
  raises **only** at `phase == '6-finalize'`, so a `verify --phase 5-execute` never raises the block.
- `automatic-review/` (SKILL + workflow) — **no** `phase_handshake` / `findings-check` call anywhere.
- `phase-6-finalize/workflow/sonar-roundtrip.md` — **no** such call.
- `phase-6-finalize/standards/branch-cleanup.md` — **no** such call. It *refers* to "the existing
  `phase_handshake findings-check` gate" (line 655) as if wired, but never invokes it.
- `cmd_findings_check` (`_handshake_commands.py`) — the read-only gate that raises
  `blocking_findings_present` on pending actionable findings at `--phase 6-finalize` — is **defined,
  documented, and tested**, but **invoked by no orchestration workflow doc**.
- `capture --phase 6-finalize` — described only in prose in
  `ref-workflow-architecture/standards/findings-pipeline.md` (the "issued by the Phase Entry Protocol"
  / "re-issued by automatic-review / sonar-roundtrip" rows) and in
  `plan-marshall/references/phase-handshake.md` (the intra-finalize `findings-check` rows). **Neither
  prose claim is backed by an actual call site.**

**Answer to the universal-vs-incidental gate:** the missing finalize-phase handshake row is
**UNIVERSAL, not incidental** — no code path emits a finalize-phase capture or findings-check, so the
row is structurally absent on every orchestrated plan. The blocking-findings gate has been **inert
fleet-wide**. Per the plan's D1 branch, **D2 is a correctness fix, not a hardening.** The reference
docs that assert the re-issue exists are **stale/false claims** and are corrected as part of D2.

### D2 — the absence of a finalize-phase handshake row is itself a blocking condition

**Design chosen — convert arming from a call to a state.** The blocking-findings raise fires only when
a `capture`/`findings-check` carrying `--phase 6-finalize` is issued (`_invariants.py`
`_capture_pending_findings_blocking_count`, guarded on `phase in _BLOCKING_BOUNDARIES = {'6-finalize'}`).
No orchestration issued one, so the gate was inert. The self-review findings the gate exists to catch are
filed **during** finalize, so the 5→6 **entry** boundary cannot catch them; the gate must live at the
finalize **merge / completion** boundary. Two firing sites now exist:

1. **Pre-merge (fail-closed):** `branch-cleanup.md` § "Pre-merge blocking-findings store gate" issues
   `phase_handshake findings-check --phase 6-finalize` before the merge — making the "existing
   findings-check gate" the doc already referenced (line 655) real, and blocking the merge on a pending
   actionable finding or an unevaluable query.
2. **Completion (state assertion):** `_invariants.assert_finalize_findings_clean` (self-armed at
   `6-finalize`, so a caller cannot disarm it by passing a non-guarded phase) is called by **both**
   lifecycle completion consumers in `_cmd_lifecycle.py` — `cmd_transition` completing `6-finalize` and a
   normal-completion `cmd_archive`. It refuses to mark the plan complete while an actionable finding is
   pending. A deliberate `--reason` archive (abandonment) stays exempt so a low-confidence plan is not
   stranded. On an unevaluable query the completion boundary fails open with a logged WARNING (the
   fail-closed path is owned by the pre-merge gate, where the executor is guaranteed present).

Both consumers of `_BLOCKING_BOUNDARIES` are addressed: `_invariants.py` (adds the self-arming assertion,
predicate unchanged) and `_cmd_lifecycle.py` (calls it from both terminal paths).

**Commits:** `cc7f7a9` (core + tests), `d03cdf8` (pre-merge wiring + doc corrections).

**Negative / positive controls** (`test_manage_status_transition.py`): a pending actionable finding
REFUSES both `cmd_transition --completed 6-finalize` and a normal `cmd_archive`
(`blocking_findings_present`, state unchanged); a clean plan is admitted; a knowledge-type finding never
blocks; a `--reason` archive bypasses; a dry-run does not fire. The negative controls exercise the REAL
predicate via the `_stub_finding_queries` seam and fail against the pre-fix code (which has no completion
gate). Plus a direct `assert_finalize_findings_clean` test in `test_phase_handshake_findings.py`
(raises on pending at 6-finalize with no caller-supplied phase; returns 0 clean; None unevaluable).

### D3 — the self-review loop-back path resolves the findings whose fixes it lands

**Design chosen.** `pre-submission-self-review.md` files a Q-Gate finding per structural defect (Branch B)
but resolves none of its own, so a landed fix left the record stuck at `pending`. New evidence-gated verb
`manage-findings qgate resolve-evidenced` (`_findings_core.resolve_qgate_findings_by_evidence`) transitions
a pending Q-Gate finding to `fixed` ONLY when its `file_path` is in the caller-supplied `--changed-path`
set (the files a landed fix touched); every finding whose file the fix did NOT touch — or that has no
`file_path` — is LEFT `pending`. A premature resolution is self-correcting: the next round's re-surface
re-detects the defect and `add_qgate_finding` REOPENS the record. Wired into the self-review delta round
(Step 1): each loop-back round resolves the prior round's evidenced findings before re-surfacing.

**Commit:** `27951b7`.

**Both directions asserted** (`test_findings_store.py`): file-in-set → `fixed`; file-not-in-set →
`pending` (the important direction); no-file_path → `pending`; mixed batch partitions correctly;
already-resolved untouched; premature resolution reopened; invalid phase errors. Plus the CLI
`--changed-path` input-shape boundary test (`test_manage_findings_cli.py`).

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (3 production scripts, 4 test files), so the
full gate ran: **`./pw verify` → SUCCESS**, 19351 passed / 14 skipped (pre-existing environment guards,
none introduced by this change). Quality gate green throughout (mypy production + test, ruff, SPDX,
plugin-doctor marketplace-wide). No `uv.lock` churn (staged deliverable paths explicitly; verified clean
tree after the build). `UV_HTTP_TIMEOUT=600` was needed — the default 30s timed out fetching deps through
the direct (non-proxied) PyPI path.

## Findings

**Pre-fix negative-control record (plan Verification requirement).** The D2 negative controls
(`test_transition_finalize_refuses_when_actionable_finding_pending`,
`test_archive_refuses_when_actionable_finding_pending`) fail against the pre-fix code: the independent
verification sub-agent confirmed via `git show origin/main:_cmd_lifecycle.py` that the pre-fix module has
zero references to `assert_finalize_findings_clean` / `blocking_findings` / `_finalize_findings_refusal`,
so pre-fix a pending actionable finding does NOT prevent `cmd_transition --completed 6-finalize` from
setting `current_phase='complete'` nor a no-reason `cmd_archive` from moving the directory — both return
success. The gate exists only post-fix; the controls therefore demonstrate the change rather than pass
vacuously.

**Verification sub-agent (independent, `general-purpose`) — pass 1.** Verdict: D1 derivation sound; D2
implemented with both consumers covered, negative control confirmed to fail pre-fix, non-vacuous,
abandonment exemption correctly scoped; D3 both directions asserted, no false-fixed path. It found **six
stale-claim gaps in UNTOUCHED files** (the change makes the old arming mechanism false) and **one
over-broad gate interaction** — all recorded per-instance below with disposition:

1. `workflow-integration-git/standards/worktree-handling.md` — "the phase-6-finalize orchestrator already
   does this for the automated-review → branch-cleanup and sonar-roundtrip → next boundaries". **Fixed**
   (commit `491ccd8`) → corrected to the real pre-merge `findings-check` example.
2. `plan-marshall/SKILL.md` guarded-boundaries list still named the never-wired intra-finalize re-issues.
   **Fixed** → replaced with the two real firing sites + the "5→6 is not a firing site" note.
3. `ref-workflow-architecture/standards/findings-pipeline.md` ASCII diagram box named "6-finalize entry +
   intra-finalize re-issues", and the prose pointed to it as "the current wiring state". **Fixed** →
   diagram box and prose corrected (box width preserved).
4. `plan-marshall/references/phase-handshake.md` findings-check verb doc said "intra-finalize
   **boundaries**" / "the intra-finalize **callers**" (plural) / "advance to branch-cleanup". **Fixed** →
   singular pre-merge caller; halt-the-merge phrasing.
5. `plan-marshall/scripts/_handshake_commands.py` `cmd_findings_check` docstring "the two intra-finalize
   callers". **Fixed** → pre-merge findings-check caller + composite capture.
6. `plan-marshall/scripts/phase_handshake.py` CLI docstring "intra-finalize boundaries". **Fixed** →
   pre-merge finalize gate.
7. Archive-gate interaction: the no-reason `cmd_archive` gate would fire on the `planning.md` cleanup pass
   that archives already-`complete` plans, so a legacy plan carrying a stale pending record (the pre-D3
   residue) could be refused at cleanup. **Fixed** → gate scoped to `current_phase == '6-finalize'`, with
   a new `test_archive_of_already_complete_plan_not_blocked_by_pending_finding` exemption test.

Two minor observations the sub-agent raised were **not acted on** with reasons: (a) the run report was
"in progress" at pass-1 time — expected, it is finalized as the last pre-merge commit; (b) the
`--reason` help text lists `normal_completion` as an example value — a latent bypass token, but no
production caller passes it, so it is left as-is (out of this plan's scope).

Re-verification (pass 2) after the fixes was dispatched; its result is recorded in the Contract check.

CI / PR-review findings: recorded after the review cycle (§ below).

## Reviewer participation

_recorded after the review cycle_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
