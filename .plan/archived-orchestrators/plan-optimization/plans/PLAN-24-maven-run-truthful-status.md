# PLAN-24: maven-run-truthful-status

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Operator-surfaced 2026-07-20 as an independent defect in the same bundle as PLAN-23.
> **Status: the SYMPTOM is operator-reported (now across TWO repos and TWO command seams) and NOT yet
> orchestrator-reproduced; a plausible MECHANISM has been verified in source (below). Re-ground and
> reproduce at outline before implementing.**
>
> **CORROBORATION + SCOPE EXPANSION (2026-07-21, separate-repo reports):** two further occurrences
> surfaced from a separate repo, promoting this from a one-session fluke to a cross-repo, cross-command
> class: (1) another `maven run` `status: success` over a real `BUILD FAILURE` (same shape as the
> original) — de-risks the "not yet reproduced" caveat; (2) `maven verify` reported **green while 3
> tests ERRORED** — the SAME untruthful-status class at a SECOND seam (test-result aggregation, not the
> build return code). Outline MUST determine whether both seams share the `success_result()` root
> (below) or diverge — do not assume one fix covers both. Reports are operator-relayed from another
> repo's lesson, consistent with this spec's existing operator-reported evidence status.

## Objective

`plan-marshall:build-maven:maven run` returned `status: success, exit_code: 0` over a real Maven
**BUILD FAILURE** — three times in one session. A build wrapper that reports success over a failure is
the highest-severity shape of this epic's recurring theme: the pipeline reports a state it has not
earned, and every downstream gate that trusts it inherits the lie.

## Evidence and current state

- **Operator-reported (not yet reproduced by the orchestrator):** three occurrences in one session of
  `run` returning `status: success` / `exit_code: 0` over a genuine `BUILD FAILURE`, plus a further
  separate-repo occurrence of the same `run`-over-`BUILD FAILURE` shape (2026-07-21).
- **Second seam, same class (separate-repo, 2026-07-21):** `maven verify` reported **green while 3
  tests ERRORED**. A green build masking test errors is severe for a green-gated project. This is
  distinct from the `run`/`BUILD FAILURE` case in WHERE truth is lost — a test-result-aggregation seam
  rather than the process return code — but identical in class (untruthful green). Whether it shares the
  `success_result()` root or is a separate parsing seam is an OUTLINE question, not a settled fact.
- **Plausible mechanism, VERIFIED in source:** `script-shared/scripts/build/_build_result.py:228-256` —
  `success_result()` **hardcodes** `'status': STATUS_SUCCESS` and `'exit_code': 0`. Truthfulness
  therefore depends entirely on the caller choosing `error_result()` vs `success_result()`; nothing in
  the result constructor derives status from the real process return code. If the maven path selects
  `success_result` on anything other than the true `returncode` (e.g. a log-pattern branch, a swallowed
  wrapper exit, or a non-zero code that never reaches the branch), the hardcoded `exit_code: 0` is
  emitted regardless of reality.
- **Known related class:** the project already knows `pyproject_build` exits 0 on failure and callers
  must read the TOON `status`/`errors[]`. **This defect is strictly worse** — here the TOON `status`
  ITSELF said `success`, so the documented mitigation ("read the status field") does not save the caller.

## Deliverables

### D1 — reproduce and root-cause

Reproduce BOTH reported seams and trace exactly where truth is lost in each: (a) a real Maven
`BUILD FAILURE` through `maven run` (does a non-zero return code become `status: success`?), and
(b) a Maven `verify` with **erroring tests** (does a test-error aggregation report green?). **Do not
fix on the hypothesis above** — it is a mechanism candidate, not a confirmed root cause, and it may
explain (a) but not (b). **Acceptance:** a written root cause for EACH seam naming the precise call
path and the condition under which the untruthful status is emitted, an explicit determination of
whether the two share the `success_result()` root or are distinct seams, and a failing test
reproducing each.

### D2 — derive status from the process outcome, fail closed

Make the result truthful at the seam: status/exit_code derive from the actual process return code, and
an indeterminate outcome resolves to **error/unknown, never success** (the ADR-009 fail-closed posture
PLAN-13 #950 encoded). **Confirm the blast radius at outline** — `success_result()` is shared, so check
whether other build tools (gradle, pyproject, npm) select it on the same unsound basis; if the defect is
in the shared constructor's contract rather than the maven caller, fix it there and sweep the callers.
**The sweep now explicitly includes `maven verify` (the Report-2 seam) alongside `maven run`** — and,
if the verify/test-error case proves to be a distinct test-result-aggregation seam rather than the
shared `success_result()` root, fix it there too rather than declaring it out of scope. **Acceptance:**
a failing Maven build yields `status: error` with the real non-zero `exit_code`; a `verify` with
erroring tests yields `status: error` (never green); a successful build/verify is unchanged; an
indeterminate/unparseable outcome never yields `success`. Regression test per affected caller AND per
affected seam (`run`/BUILD-FAILURE and `verify`/test-error).

### D3 — guard the constructor contract

Prevent a caller from re-introducing this: make it structurally hard to emit `success` while holding a
non-zero return code (e.g. `success_result()` asserts/accepts the observed return code rather than
hardcoding 0, or a structural check). Mirror the pattern PLAN-13 #950 D4 used for fail-closed
provisioning writes. **Acceptance:** a new caller that reports success over a non-zero return code is
caught by a test or structural check, not by a user noticing a green build that failed.

## Out of scope / do NOT expand
- Marker scanning / the `search-markers` relocation — that is **PLAN-23**.
- The `pyproject_build` exit-code behavior, unless D2's sweep finds it shares the same unsound seam —
  in which case note it and confirm scope at outline rather than silently widening.
- Maven output *parsing* features beyond what truthful status requires.

## Absorbs
- Operator-surfaced defect "`build-maven:maven run` returned success over a real BUILD FAILURE ×3"
  (2026-07-20), explicitly filed as its own entry.
- Separate-repo corroboration (2026-07-21): a further `maven run` success-over-`BUILD FAILURE`
  occurrence → strengthens D1's reproduction target (cross-repo, not one-session).
- Separate-repo defect (2026-07-21): `maven verify` reported green while 3 tests ERRORED → the
  second seam folded into D1 (reproduce) + D2 (fix/sweep + acceptance). NOT a separate plan.

## Expected Surface
- `build-maven/scripts/maven.py` — `run` path status derivation
- `script-shared/scripts/build/_build_result.py:228-256` (`success_result` / `error_result` contract)
- `_build_execute.py` / `_build_execute_factory.py` — where the return code is observed
- the `maven verify` path's test-result aggregation (Report-2 seam) — where an erroring test-run
  becomes green; confirm at outline whether it routes through `success_result()` or a separate parser
- possibly `build-gradle` / `build-pyproject` / other callers (D2 sweep)
- tests: failing-build-yields-error; verify-with-test-errors-yields-error; successful-build-unchanged;
  indeterminate-never-success; structural guard

## Dependencies and Sequencing
- Depends on: none.
- **Adjacent to PLAN-23** on `build-maven/scripts/maven.py` — different regions (PLAN-23 removes a
  subparser registration; this changes `run`'s status derivation). Trivial rebase expected; startable in
  parallel, rebase whichever lands second.
- Surface-disjoint from PLAN-18/20/21/22. Note D2's sweep may touch `script-shared/build`, which
  **PLAN-20** also touches (`_test_scope_divergence.py`) — different files; watch for it at outline.

## Size / split guard
3 deliverables — under the ~6 presumption. D2's caller sweep is the elastic one: if the unsound seam
proves shared across many build tools, ship the maven fix + the guard and stage the remaining callers as
a follow-up, recorded as an epic decision.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-24-maven-run-truthful-status.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-24.md is recorded}
