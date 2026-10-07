# Landing Analysis: PLAN-24 — Maven Run Truthful Status

epic: plan-optimization
workstream: WS-10
pr: #963 (`c865a2938`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.
>
> **Record history — this analysis was written twice.** A first pass was written diff-only,
> because the merge was discovered incidentally (`git log main` showed `c865a2938` above
> PLAN-28's `cd931fb63`) with no narrative supplied. The operator narrative arrived
> afterwards and **falsified two claims in that first pass**; both are corrected below and
> the errors are recorded rather than quietly overwritten, because the failure mode they
> illustrate is itself a finding.

## ⚠ Corrections to the First-Pass Analysis

Two claims in the diff-only pass were **wrong**:

1. **"Premise confirmed" — FALSE.** The first pass concluded the orchestrator's source-level
   mechanism read *held up*, namely that `_build_result.py`'s `success_result()` hardcoding
   `status: success` / `exit_code: 0` was the root cause. The narrative states plainly that
   **neither** call path was rooted in that hardcoding. The staged spec's hypothesis was
   **falsified**, and PLAN-24 joins PLAN-17/18/19 as a plan whose premise did NOT survive
   re-grounding — the opposite of what the first pass recorded. The spec's instruction *"D1
   reproduce+root-cause, do NOT fix on the hypothesis"* is what saved the plan; had it been
   implemented against the orchestrator's stated mechanism it would have fixed the wrong thing.
2. **"3/3 deliverables" — WRONG COUNT.** The first pass inferred three deliverables from the
   staged spec and reported `3/3 shipped-as-specified`. The plan actually shipped **2**.

**Root lesson for this orchestrator:** a diff can confirm *that* a defect was fixed, but not
*which hypothesis* was right or *what the plan's own deliverable structure was*. The first pass
overstated its confidence — it read "both seams confirmed" in the PR body as vindication of the
epic's mechanism, when the PR body was in fact describing a different mechanism at a different
call site. Diff-only landing records must state seam-level findings as **observed**, never as
**premise-confirming**.

## Deliverable Fidelity vs Spec

Verified against merge commit `c865a2938` (7 files, +361/-17) and the operator narrative.
**2 deliverables, both shipped.**

| Deliverable (as executed) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — derive truthful Maven status at both seams, fail-closed (`cmd_run_common` + `cmd_parse_common`, regression tests + `testFailureIgnore` fixture) | shipped | `_build_shared.py` (+72). **Seam (a)** `cmd_run_common` trusted `returncode == 0` and emitted success without cross-checking `test_summary` — the testFailureIgnore / exit-0-with-test-errors window. **Seam (b)** `cmd_parse_common` derived status from the `build_status` string alone, ignoring `test_summary.failed`. Both fail-closed per **ADR-009**, each with a per-seam failing-then-passing regression test. Reproduction was real, not asserted: `maven-testfailureignore-green.log` (+27) is a genuine `BUILD SUCCESS` log carrying `Errors: M>0`, and `mvnw-testfailureignore.sh` (+51) a mock wrapper exiting 0 while emitting it |
| D2 — `assert_truthful_status` structural guard wired into the success-emit choke points | shipped | `_build_result.py` (+37), raising `TruthfulStatusError` at the emit choke point so a caller can never again emit `status=success` while holding a non-zero outcome. Covered by `test_truthful_status_guard.py` (+114), `test_maven_run.py` (+38), `test_maven_cmd_parse.py` (+39) |

**Premise FALSIFIED, plan succeeded anyway.** The staged spec's mechanism
(`success_result()` hardcoding) was wrong; the real defect was two distinct call paths in
`_build_shared.py` that never cross-checked the parsed test summary. The plan found this because
D1 was scoped as *reproduce-and-root-cause first*. This is a **direct vindication of the
do-not-fix-on-the-hypothesis discipline** the epic has been applying since PLAN-17, and the
strongest datapoint yet for keeping it in every spec whose mechanism is orchestrator-inferred
rather than observed.

## Metrics and Anomalies

- Tokens: 3M
- Duration: 2h20m worked
- Finalize: 21/21 steps done; pre-push quality-gate + whole-tree tests green; plugin-doctor
  clean (1 skill gated); self-review clean (16 candidates); `finalize-step-simplify` made 1 edit
  (removed a redundant guard) then 0 on re-fire
- Deploy: 1105 files, bundles → **v0.1.1174**; 10 bundles synced, on-main executor regenerated
- Anomalies: none in execution. One observable in the PR body — the Test Plan checkboxes are
  unticked (`- [ ]`), unlike #962's; required CI checks were green at merge, so noted, not a defect.

## Routing and Merge Behavior

- **Review**: **gemini caught 2 real defects in the plan's own D2 guard** — it was checking a
  tautologically-zero `exit_code` (never forwarded) and misfired on explicit `None`. Fixed via
  loop-back (TASK-005/006), re-pushed, re-verified green, threads resolved. Review-retrospective:
  gemini 2/2 actionable, **100% resolved-as-fixed**. The slipped-then-caught defect became
  **lesson `2026-07-21-14-002`**.
  - ⚠ **Same shape as PLAN-20 and PLAN-28: the review bots' highest-value findings keep landing
    in the plan's OWN newly-authored guard code.** A guard written to enforce truthfulness was
    itself untruthful (checking a value never populated). Three consecutive landings where the
    new structural guard was the defect site.
  - **Fifth consecutive landing where sunset-flagged gemini produced real findings** (PLAN-20,
    PLAN-22, PLAN-28, and here 2/2 actionable at 100% fixed).
- **CI/merge**: rebased, merged via queue (squash), branch cleaned up. Landed at `c865a2938`,
  directly above PLAN-28's `cd931fb63` — ~23 minutes apart (14:45 and 15:08 UTC+2).
- **Surface collisions**: **none — and this is the notable result.** PLAN-24 and PLAN-28 merged
  back-to-back while PLAN-25/26/30 were also in flight (five concurrent plans, the widest this
  epic has run). Every predicted disjointness held; no rebase conflicts, no re-verify signals.
  The surface-disjointness pairing model is validated at five-way concurrency.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `963`, landing `landings/PLAN-24.md`)
- [x] epic.md queue row reconciled from status.json
- [x] Sequencing unblocked: **PLAN-23** was ADJACENT to live PLAN-24 on `maven.py` — that block
      is now CLEARED, which in turn unblocks **PLAN-27** (depends on PLAN-23)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **PLAN-23 is now emittable** on the maven surface (its ADJACENT-to-live-24 hold is released).
  Note the landing touched `script-shared/scripts/build/_build_shared.py` and `_build_result.py`
  but **not** `build-maven/scripts/maven.py` itself — PLAN-23's marker-detector work should
  re-ground against the post-#963 tree before assuming its cited line numbers still hold.
- **⚠ CROSS-PLAN ORDERING GAP — a fix on main does NOT reach concurrently-running plans.**
  `lessons-housekeeping` tried to promote lesson `2026-07-21-14-002`'s rule into
  `persona-module-tester/testing-methodology.md`, but PLAN-24's manifest was **composed pre-merge
  with the OLD post-merge ordering**, so the edit could not ride the already-merged PR. PLAN-28
  (#962) had *already fixed that ordering on main* — but a composed manifest is a snapshot, so
  the fix could not retroactively apply to a plan already in flight. Correct disposition taken:
  per `source-edit-pushability.md` the stranded edit was reverted and follow-up lesson
  **`2026-07-21-15-002`** filed, rather than pushing unreviewed to main.
  - This **validates PLAN-28's fix** while exposing its migration boundary: every plan whose
    manifest was composed before `cd931fb63` still carries the old ordering. PLAN-25/26/30 were
    all in flight at that moment and may be affected.
  - **Owed work**: re-run the deferred promotion of `2026-07-21-14-002` via a normal plan; it
    will land cleanly now that main carries the corrected ordering.
- **Landing-record completeness gap** (already a watch). This plan is the proof case: the
  narrative arrived only after a diff-only record had been written, and it falsified two of that
  record's claims. Nothing detects a merged PR whose plan never reported in.
- **Executor regenerated to v0.1.1174** — session-restart guardrail applies.
