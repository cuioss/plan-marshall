# Landing Analysis: PLAN-TRUTH-087 — build-gates-test-suite-confidence-and-ci-workflow-lint

epic: truthful-signals
workstream: WS-01
pr: #1340 — merged, squash via platform merge queue, `b5ee8fac7`

> Landing record for one shipped plan. Lives at `landings/PLAN-TRUTH-087.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Two inputs, one landing: an operator paste and the plan's own `kind: landing` message (`-013`).
`inbox landing-check` returned `complete: true`, `missing_keys[0]`. 13 messages drained.

⚠ **#1340 merged AFTER #1343/#1344/#1345/#1346 despite the lower number** — a long-lived branch
admitted late by the merge queue. Verified against `git log`, not inferred from the number.

## Deliverable Fidelity vs Spec

9 of 9 shipped. The `steps` fact lists **23 steps, every one `done`** (parsed with the mandated
LAST-colon split — `project:finalize-step-lessons-housekeeping:done` and
`plan-marshall:plan-retrospective:done` both recover correctly).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 derive five populations or halt | shipped-as-specified | `_plan_state_exemption.py`, `_porcelain.py` in `b5ee8fac7` |
| D2 unify trackedness oracle + porcelain encoding | shipped-as-specified | same commit; `build-api-reference.md` |
| D3 published build counts and status vocabularies | shipped-as-specified | `script-shared/scripts/build/*` |
| D4 marker-write guard enforces what it reports | shipped-as-specified | `_gate_coverage.py`, `build.py` |
| D5 build-gate coverage verdicts stop overstating | shipped-as-specified | `test/default/test_build_verify.py` |
| D6 workflow-lint guard covers its docstring's shapes | shipped-as-specified | `test/default/test_workflow_lint.py` |
| D7 multi-target generator emitter/corrupt-input/prune | shipped-as-specified | `equality_check.py`, `opencode/emitter.py` |
| D8 pollution-guard scope, sandbox ownership, zero-skip | shipped-as-specified | `post_run_source_guard.py` |
| D9 evidence artifact + 31-gap closure ledger | shipped-as-specified | PR body enumerates the 31 gap ids |

## ⛔ Two landing claims CONTRADICTED at ground truth

**1. The "14-file new skill inside this PR" claim is false for #1340.** The landing's Residue says
*"28 modified files sit outside every deliverable's declared surface, 14 of them one coherent new
skill (`pm-plugin-development:tools-epic-surface-partition`) that no deliverable names."*
Measured: **#1340 contains ZERO `tools-epic-surface-partition` files.** That skill landed in
**#1345** (`00b92fca3`, 12 of its 14 files). The Residue describes the **worktree at retrospective
time**, not the merged PR. ⇒ Do not carry the 14-file figure as a property of this landing.

**2. "Declared-surface recall was 100% (44/44)" is not reproducible.** An independent path-exact
measurement at the drain gives **30 of 41 declared paths present in the merged diff (73.2%)**, with
**26 substantive undeclared files** (>4 changed lines, 55 substantive of 58 total).

⚠ **Neither number is trustworthy, and that is the actual finding.** The `## Expected Surface`
section is prose: abbreviated paths (`.../script-shared/scripts/`), bare filenames
(`_build_parse.py`), and glob fragments (`.github/workflows/**`). A path-exact matcher under-counts
it; whatever the plan used over-counted. **The declared surface has no machine-readable form, so
two honest measurements of the same quantity disagree by 27 points.** ⇒ Folded to `PLAN-TRUTH-113`
as first-party evidence; this is precisely its D0.

## Metrics and Anomalies

- Tokens **11,170,290 (n=5/6)**; billing **59,120,898** — recorded on `6-finalize` alone.
- **`6-finalize` dominated: 9,339,125 tokens and 6h44m worked of 8h51m total.** `5-execute` was
  349,182 tokens against a 32h33m wall — an idle-dominated phase.
- Wall 53h18m against 8h51m worked.
- `any_phase_missing_end_time=false` — unlike `-094`, this landing's total is **not** flagged a floor.
- **Three of five operator turns were bare nudges** (`retry`, `contniue`, `contniue`): the run
  stalled and needed hand-restarting three times. No metric or step record captures this.

## Routing and Merge Behavior

- **`participation_complete: true` proved participation only.** pr-agent (required) published an
  empty clean guide; CodeRabbit was credited on stale evidence, rate-limited off the final HEAD;
  Sourcery reviewed nothing at any point. The merge was authorized correctly; the diff was not
  thoroughly reviewed. ⇒ forwarded to `review-apparatus` as `truthful-signals-037.md`.
- CodeRabbit's unreviewed delta is a 4-line test refactor **it had itself requested**.
- `pr-agent` resolved `participated_stale`; **Trigger B selects from the most recent bot-authored
  finding, which by then stamps the current HEAD, so it would skip forever.** An explicit `/review`
  was fired by hand.
- **Mid-finalize rebase, hand-resolved**: branch `mergeable: conflicting` against a main advanced by
  7 commits; 24 commits replayed, 3 carrying conflicts across 7 files. **No step records it** — see
  the false `done` below.
- 8 plugin-doctor findings were **stale-executor artifacts**, cleared by regeneration with zero
  source edits.

## ⛔ The mid-run config change that became permanent

**The loop-back ceiling was raised 3 → 8 mid-run to unblock this plan, and it is now the committed
project default for every future finalize.** Verified first-party: `.plan/marshal.json` **is a
tracked file** (an exception to the `.plan/` gitignore), and `b5ee8fac7` is its most recent
modifier. The entire diff it carried is:

```diff
-      "max_iterations": 3,
+      "max_iterations": 8,
```

⚠ The raise was load-bearing for this run — 6 iterations were spent, so at 3 (or even 5) it would
have halted with findings unreviewed. That is not in dispute. What is: **a per-run exception rode
into main inside the plan's own footprint and silently became standing policy.** There is no
decision-log entry and no step record; the only trace is the config line itself. ⇒ Operator decision
owed — keep 8 as the default, or revert and make per-run raises explicit and scoped.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — `#1340`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-087.md`
- [x] row `plan_marshall_plan_id` — already stamped
- [x] 13 messages dispositioned and archived
- [x] `2026-08-09-13-001` refined (deletion is necessary, not sufficient)
- [x] 2 lessons promoted; head-dependence pair folded to `-097`; surface evidence folded to `-113`
- [x] review findings forwarded to `review-apparatus`
- [x] START-HERE and Ordered Queue regenerated

## Follow-Ups

- **4 owed `architecture enrich insight` calls are UNISSUED** (`-005`…`-008`). The module record
  carries **zero** insights, so none has been applied. The retrospective flagged possible overlap
  with an earlier set; **resolved at the drain — not duplicates.** The archive holds two prior
  hints, and the only near-match is *"improvement findings are a standing consideration"* for module
  **`orchestrator`**, where `-005` is the same insight for module **`plan-marshall`**. Per-module
  insights; both legitimate. ⇒ Handed to the operator; the orchestrator does not mutate the
  architecture store.
- **Daemon reconcile owed** (`owed: true`, `defer_count: 1`) — `marshalld` was busy at cache-sync
  time and deferred rather than draining a live build. Still on the pre-`0.1.1547` pin.
- **Two unfixed instrument defects** (actionable_count inflated 18→20 by an empty-`body` finding
  defaulting to `actionable`; the retrospective cannot see `cuioss-review-bot`) → `review-apparatus`.
- **#1345 and #1346 landed unanalyzed** — `tools-epic-surface-partition` and ADR-019 (*"an audit
  separates unevaluated from evaluated-and-clean"*). ADR-019's subject is squarely this epic's theme
  and it landed without passing through this ledger.
