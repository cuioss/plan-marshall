# Run report — 180-finalize-dispatch-manifest-observability (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/finalize-dispatch-manifest-observability-nrxcwr` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, governs the run).
- `plan-marshall:ref-code-quality` (read by bundle path).
- `pm-plugin-development:plugin-script-architecture` (read by bundle path).

_Additional domain skills loaded as the surface is confirmed (Python production/tests, plugin-architecture, workflow-architecture)._

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Ordering constraint (Notes) — re-derived from the clone

The plan carries a hard ordering constraint: (1) the sibling audit plan (170) runs FIRST; (2) the
other epic's roster correction lands before D6. Both re-derived from the clone rather than trusted:

- **Sibling audit (plan 170) LANDED.** `c93431f fix(plan-retrospective): make the dispatch audit
  deterministic and fail-able (#1225)` is on `origin/main`. The dispatch audit is now a deterministic,
  fail-able detector (`check-dispatch-audit.py`), so this plan can measure its own divergence.
- **Roster correction LANDED.** The roster (`dispatch-inline-split.md`) already classifies
  `default:architecture-refresh` as **inline** (agreeing with its standards doc's inline
  self-classification), and `test_dispatch_roster_closure.py` check (f) already enforces that
  agreement with a mutation guard reproducing the pre-fix (dispatched-roster) shape. The
  architecture-refresh classification divergence is already corrected at HEAD.
- **Seam producer LANDED.** `1da26b1 fix(dispatch-audit): emit the dispatch record from the
  resolve-target seam, per firing (#1200)` wired `_cmd_effort.py::_emit_dispatch_records`, which emits
  `[DISPATCH]` (work-log) + the decision-log record per-firing when `effort resolve-target` is passed
  `--workflow`. Plan 170's report Residue explicitly names "the sibling emission plan" (this plan) as
  owner of migrating finalize resolves to that seam.

## Deliverables

### D1 — GATE: map the observability seams (mutates nothing)

Each defect confirmed or refuted at its own site at HEAD. Split re-evaluated at outline: proceeding
unsplit is upheld — D2/D3/D6 share one surface (the dispatch/step emission seams and their tests) and
splitting would race on `phase-6-finalize/SKILL.md` and `test_dispatch_roster_closure.py`.

| Defect (Problem) | Deliverable | Verdict at HEAD | Write seam |
|---|---|---|---|
| Dispatch line wired to first entry, not spawn | D2 | **CONFIRMED (live).** Finalize hand-writes `[DISPATCH]` at 3 sites (SKILL.md ~600, ~982, ~1417) and passes NO `--workflow` to its `effort resolve-target` calls, so the per-firing seam never fires for finalize — the forbidden per-role hand-written pattern `dispatch-logging.md` replaced. | `effort resolve-target` seam (`_cmd_effort.py::_emit_dispatch_records`, landed #1200) |
| Step markers per-handler, population path-dependent | D3 (part 1) | **CONFIRMED (live).** Completion emission is 5 hand-written per-handler sites (SKILL.md 822/887/941/1117/1238), a convention enforced by a test rather than fused to the write. | `mark-step-done` (`_cmd_mark_step.py`) |
| Handshake and log line are two separate obligations | D3 (part 2) | **CONFIRMED (live).** `mark-step-done` writes only the status record (no logging import); the `[STEP] Completed step:` line is separate prose. | `mark-step-done` |
| head-at-completion peer omittable | D3 (peer) | **REFUTED.** Fail-closed guard already refuses a head-dependent `done` without `--head-at-completion` (`_cmd_mark_step.py:274-290`), and the read side re-fires + reports UNVERIFIED for a legacy SHA-less record (SKILL.md:661-662). Peer already closed both directions. |
| Resume path emits no step instrumentation | D4 | **REFUTED.** No separate resume mode; re-entry is one unified FOR loop (SKILL.md:641,652,1685). Every EXECUTED step emits item-2 start (:708) + item-7 completion (:1238). Only intentional SKIP branches omit the completion line, and they still log an INFO skip-decision line (:692–702). The epic `plan-orchestrator/workflow/resume.md` never re-runs finalize steps. Coverage-population note (D4 obligation): there is no resume-specific population because observability is uniform across the single re-entry mechanism. |
| Retrospective mode keys on wrong signal | D5 | **REFUTED (failure unreachable).** Mode still keys on `--iteration` presence (`plan-retrospective/SKILL.md:74`), and user-invocable mode writes no tail (:36,:423) — but the finalize dispatch **forwards `--iteration`** (`phase-6-finalize/SKILL.md:1007`), landing in the record-WRITING mode, and `external-step-contract.md:24` + the dispatcher's `assert-step-recorded --require-terminal` guard (SKILL.md:1088-1117) backstop any missing record with an attributed halt. D5's "done when" (dispatch selects intended mode AND record written) is already met. Version-stale flag confirmed: the tail now carries payload in two shapes. |
| Roster contradicts its own closure invariant; classification wrong | D6 | **PARTIALLY LIVE.** The known divergence (`architecture-refresh` dispatched-in-roster vs inline-in-doc) is ALREADY corrected — roster + doc agree, and check (f) in `test_dispatch_roster_closure.py` already reads both docs with a mutation guard reproducing the pre-fix shape. Residue: check (f)'s file population is **pinned** (`_D5E_STEP_DOC_PATHS`), not derived from the roster/registry population. D6's "done when" (derived, not pinned) is the remaining gap. |

**Ordering constraint** (Notes) re-derived from the clone — both satisfied (see § Ordering constraint).

Live work: **D2, D3, D6.** Refuted with evidence: **D4, D5, D3-peer.**

### D2 — emit the dispatch line from the resolve seam, per spawn — **DONE** (commit `23c7df8`)

Migrated all four finalize `effort resolve-target` sites (the agent-suitable-built-in preamble, the
item-5 built-in and project/skill branches, the item-7c unified-triage hook) to pass
`--workflow`/`--plan-id`/`--caller plan-marshall:phase-6-finalize`, so the resolve seam
(`_cmd_effort.py::_emit_dispatch_records`, landed #1200) emits both `[DISPATCH]` and its paired
decision-log record **per firing**; dropped the three hand-written `[DISPATCH]` blocks (they
double-emit and reintroduce the per-role blind spot). This is placement work, not contract work: the
line's shape and the seam already existed; only finalize's use of them was wrong. Migrating finalize
also makes the dispatch audit's `shape_violation` evaluable for finalize (Surface B was empty before —
plan 170's residue). Verification (N>1): the seam's per-firing property is covered by
`test_dispatch_seam_emission.py` (5 fires → 5 records; N∈{1,2,3,7}); added
`test_finalize_dispatch_emits_one_line_per_spawn` (3 finalize spawns → 3 lines under the finalize
caller). Rewrote roster-closure check (e): every `Task:` spawn is preceded by a `--workflow` seam
resolve, and no hand-written `[DISPATCH]` survives, with mutation guards on the pre-fix shape.

### D3 — fuse the completion marker to the handshake — **DONE** (commit `e9e3259`)

`mark-step-done` (`_cmd_mark_step.py::_emit_completion_marker`) now emits the
`[STEP] (plan-marshall:phase-6-finalize) Completed step: {step}` line as a side effect of every
terminal write for a `6-finalize` step, scoped to that phase so the emission surface — and the
out-of-scope dispatch audit's `completion_count` — is unchanged for every other phase. Removed the
five hand-written completion emits from SKILL.md (the two Signal-Gate skips, the dispatch-timeout
path, the post-dispatch-guard halt, the item-7 happy path) and rewrote the pairing prose: the line
now rides the handshake structurally on every recording path. Added `--no-completion-log`, carried by
exactly one call — the item-5f `head_at_completion` re-stamp, which revises an already-emitted `done`
— so exactly one line survives per step. Verified by removing the prose emit and confirming a step
still produces its marker (`test_mark_step_completion_emission.py`, 5 cases: emit / every-outcome /
suppress / phase-scope / idempotent) and rewrote `test_step_completion_emission.py` to pin the
fusion's two structural invariants (no hand-written emit survives; no terminal-exit block suppresses
the fused emission), with mutation guards. **Peer (`head_at_completion`) REFUTED, left unchanged** —
the fail-closed guard already refuses a head-dependent `done` without a SHA (`_cmd_mark_step.py:274`),
closing the peer from both directions.

### D4 — the resume path emits step instrumentation — **REFUTED at HEAD** (no change)

There is no separate resume mode. Re-entry is one unified FOR loop (SKILL.md:641,652,1685); every
step it EXECUTES emits its item-2 start and item-3-fused (was item-7) completion marker. Only
intentional SKIP branches omit the completion line, and they log an INFO skip-decision line
(SKILL.md:686). The epic `plan-orchestrator/workflow/resume.md` never re-runs finalize steps. **D4's
coverage-population obligation** ("any coverage figure must state whether its population included a
resume"): there is no resume-specific population, because observability is uniform across the single
re-entry mechanism — a step that executes is instrumented regardless of how the run re-entered.

### D5 — fix the retrospective mode-resolution signal — **REFUTED at HEAD** (no change)

The claim-labelled HYPOTHESIS — "the retrospective's mode resolution keys on an argument **the
dispatch does not pass**" — is **false at HEAD**. The authoritative Mode-resolution rule
(`plan-retrospective/SKILL.md:70`) keys on "invoked by `phase-6-finalize`"; the detection heuristic
(:74) uses `--iteration` presence as the observable proxy for that, and the finalize dispatcher
**always forwards `--iteration`** — the generic dispatched project/skill branch passes
`--iteration {iteration}` (SKILL.md item 5), and `loop_back_iteration` is always defined (≥0). So the
retrospective always lands in the record-writing finalize-step mode, and its `mark-step-done` tail is
written. Two independent backstops guarantee the record regardless: `external-step-contract.md:24`
(every external step MUST terminate with `mark-step-done`) and the dispatcher's
`assert-step-recorded --require-terminal` guard (SKILL.md item 5d), which converts any missing record
into an attributed `step_record_missing` halt. Version-stale flag confirmed (the tail now carries
payload in two shapes). D5's "done when" (dispatch selects the intended mode AND record written) holds
at HEAD; a speculative edit to the working, backstopped, multi-consumer mode-resolution mechanism is
not a proposal (lane rule), so none is made.

### D6 — correctness assertion over the roster, derived not pinned — **DONE** (commit `0ee7375`)

The cross-document **correctness** check (roster classification vs the step's own doc
self-classification) already existed as check (f) in `test_dispatch_roster_closure.py`, but read its
population from a hardcoded file list (`_D5E_STEP_DOC_PATHS`) — a hand-maintained mirror of a derived
set, the exact archetype the plan forbids (n≥5). De-pinned it: the population is now DERIVED from the
finalize-step registry via `find_implementors` (the same discovery the dispatcher and head-dependence
use), so every registered step's own doc is read for a self-classification sentence with no pinned
list. Replaced the pinned-existence guard with a registry non-degeneracy guard; kept the mutation
guard. **Verified the derived check FAILS against the divergent state** (Verification requirement):
temporarily moved `architecture-refresh` to the dispatched roster and confirmed
`test_touched_step_docs_agree_with_the_roster_classification` fails — it discovered
`architecture-refresh.md` via the registry, read its `**inline**` self-classification, and flagged the
disagreement — then reverted; the test passes on the corrected tree. Did **not** add a second
hand-written pin. The known divergence (architecture-refresh dispatched-in-roster vs inline-in-doc)
was already corrected at HEAD by the other epic's roster correction (ordering constraint satisfied),
so the detector passes on the live tree and the failure is demonstrated against a reconstructed
divergence, exactly as the plan's mutation-guard discipline prescribes.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (`_cmd_mark_step.py`,
`manage-status.py`, four test files), so the build takes its full path. Per-commit `./pw quality-gate`
ran clean (`issues[0]`, `coverage: COMPLETE`) before each `*.py`-touching commit. **Full `./pw verify`:
SUCCESS — 19638 passed, 14 skipped, 0 failed; coverage COMPLETE over mypy(production, 399 files), ruff,
SPDX, plugin-doctor (marketplace-wide), mypy(test, 735 files), and whole-tree pytest** (525 s). Read
from the build output, not the exit code. One intermediate `test-compile` failure — a `no-any-return`
in the new `test_mark_step_completion_emission.py` `_mark` helper (returning the `Any` result of a
`load_script_module`-loaded `cmd_mark_step_done` from a `-> dict` function, the exact test-only type
error the lane warns `test-compile` catches that `quality-gate` + `module-tests` would miss) — fixed
by binding the result to a typed local (`a906bad`) and re-verified green.

## Findings

_Pending._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
