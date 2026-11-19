# Landing Analysis: PLAN-LB-166 — A local-only run is never given push-only steps back: "no push" always wins in the execution manifest

epic: live-blockers
workstream: WS-01
pr: #2018 (https://github.com/cuioss/plan-marshall/pull/2018)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-166-manifest-no-push-always-wins-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

PR #2018 `merged` through the CI abstraction; merge commit `8abcca327035106c4251cb19303b4d8b3423391d` (squash, parent `44753f639`), on `origin/main`, read with git. The diff is five files: `_manifest_rules.py`, `manage-execution-manifest.py`, `SKILL.md`, `standards/decision-rules.md` and one test file.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the ceremony selection honours `commit_and_push` | shipped-as-specified | re-read: `_apply_ceremony_finalize_selection` gains keyword-only `commit_and_push: bool = True` and, in its `always` branch, `continue`s when `not commit_and_push and canonical in _COMMIT_PUSH_DROP_STEPS` (`_manifest_rules.py` hunk at 787-788 and 833-836); the one production call site forwards it (`manage-execution-manifest.py` hunk at 2886-2888). The pre-filter runs at `:2571`, the selection at `:2886` (grep of the checkout, re-read). |
| D2 — a test pins it, written against the unfixed tree first | shipped-modified | the test class sits in `test_ceremony_finalize_selection_ceremony_finalize_always.py` (+126 lines), a file the spec does not name; neither named file holds the forced-`always` cases (the leaf's reading of both files; the landing says the same). The spec's own rule "whichever already holds the forced-`always` cases" points to the `_always` file, so the placement follows the rule and the spec's two file names were a false premise. |

**Surface delta** (declared 4, realized 5): declared and touched: `_manifest_rules.py`, `manage-execution-manifest.py`. Declared and untouched: `test_ceremony_finalize_selection.py`, `..._ceremony_finalize_never.py`. Realized and undeclared: `SKILL.md`, `standards/decision-rules.md`, `..._ceremony_finalize_always.py`. All five are inside `manage-execution-manifest` or its tests, so the standing constraint holds; the plan disclosed the three. The spec is shipped, so no correction is owed to it; no other staged spec declares any of these paths (PLAN-LB-165's surface is disjoint).

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`). The orchestrator re-read the points marked "re-read" at their lines; every other point is the leaf's reading and is an unverified lead. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with PLAN-LB-162's or PLAN-LB-163's, read in their own leaves in the same drain.
- **Verdict:** layer 1 findings (one minor); layer 2 findings (two minor); layer 3 findings (minor only, no major); not shown by reading on layers 2 and 3.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D2 names two files that "already hold the forced-`always` cases"; neither does, the `_always` file does | checked (leaf reading) | refutes (premise) | `test_ceremony_finalize_selection_ceremony_finalize_never.py`, `..._always.py:24-154` |
| L1-2 | D2 asks one forced-gate case for each of the four steps; `push` owns no gate, so its case cannot exist | checked (leaf reading) | confirms (D1's clause already anticipates it) | `_manifest_rules.py:658-689` |
| L1-3 | Both HYPOTHESES hold: the order lets the second function re-add what the first removed, and a `minimal` lane yields `always` | checked (leaf reading; order re-read) | confirms | `manage-execution-manifest.py:2571` and `:2886` |

**Layer 1 verdict:** findings — 1 (L1-1, minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_manifest_rules.py:787-788, 833-836`; `manage-execution-manifest.py:2887` (re-read) | the refusal tests (present-and-dropped, absent-and-insertable) go red without the guard because the `always` branch would re-insert | `SKILL.md` and `decision-rules.md` edits: the landing says D1's "records" clause requires them; the clause governs what the outline records, not documents, so no deliverable names the edits (leaf reading; minor, inside the module) | checked |
| D2 | the always-test file | the three pushing-plan controls and the out-of-set `simplify` case pass on the unfixed tree by design; the derived case set carries a non-vacuity test | the landing's "7 failed, 4 passed" runs were made before the derived case set and the non-vacuity test were added (leaf reading of the commit order, not re-read): the merged form was never shown red | checked (minor) |
| the test-first order | — | — | squash merge: whether the test run preceded commit `8f5b9775e` cannot be seen in git | not_shown_by_reading |

**Layer 2 verdict:** findings — 2 (minor); not shown by reading — 1

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `manage-execution-manifest.py:3831-3842` (re-read; unchanged by this landing) | a plan composed with `commit_and_push=false`, then a push-only step added to live `marshal.json` phase-6 steps, then `reconcile --apply` | the backfill adds every live candidate missing from the composed and frozen sets that resolves, without consulting `commit_and_push`, so the push-only step lands in a local-only plan's `phase_6.steps` | minor |
| L3-2 | `decision-rules.md:180` | reading the new text | says the drop is final and no gate value can hand a local-only plan a push-only step; true inside `compose`, too broad given L3-1 (leaf reading) | minor |
| L3-3 | `_manifest_rules.py:833-836` | `minimal` lane on `code-review` with `--commit-and-push false` | a bare `continue`: no log line, and the compose result still reports the gate as `always` while the step is absent (leaf reading) | minor |
| L3-4 | `_manifest_rules.py:788` | a future caller that omits the keyword | defaults `True`, so the guard fails open; the one production caller forwards it, and the other callers are tests (leaf reading) | minor |

**Layer 3 not shown by reading:** L3-5: that no transform after the guard adds a step to `phase_6.steps` — the lane-resolution and sort bodies were not read; and that the new tests compose to `success` with the stubbed footprint, which only a run shows.

**Layer 3 verdict:** findings — 4 (minor, none fails open on an observed input); not shown by reading — 1

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | No duplication, cross-reference | deviates | the no-push rule is restated in the docstring, a compose comment, `SKILL.md` (two places) and `decision-rules.md` (three places) (leaf reading) |
| CLAUDE.md § Commit Trailer | exactly the `plan-marshall` trailer | conforms | the squash ends with `Co-authored-by: plan-marshall <noreply@cuioss.de>`; the extra human co-author line is GitHub's squash (leaf reading) |
| spec Standing Constraints | nothing outside `manage-execution-manifest` and its tests; nothing under `.plan/orchestrator/` | conforms | the five-file diff stat (re-read) |
| ref-code-quality | fail-safe defaults; no silent decision | deviates | L3-3 and L3-4 |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope under the ruling of 2026-10-23, so no defect.
- Duration: not stated.
- Anomalies: the lane reports one guard entry (R7, a first edit aimed at the main checkout, re-issued inside the worktree) and two bound expiries on routed builds, both re-run. `.plan/temp/guard.log` was not re-read here.
- Model: `deepseek-v4.1-flash/high`, one model throughout.

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 1 body finding, 1 handled. `runbook_lane review-gate --pr-number 2018` returns `unresolved_review_threads: 0` and `review_body_findings_total: 1`, both agreeing; `handled` reads 0 from the provider by design (the disposition lives in the run's ledger). The progress file carries one `finding:` line (`coderabbit inline inline-1 — 11811e623`), so `review_body_findings_handled: 1` is **re-verified**.
- CI/merge: merged (`8abcca327`); the base was merged into the branch twice before the merge head. CodeRabbit's check-run on the merge head was NEUTRAL (bot-side limit), not a required gate.
- Sonar: `sonar_open_new_issues: n/a`; Sonar is not enabled for this project.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-166 --status shipped`
- [x] row `pr` stamped — `2018`
- [x] row `landing` stamped — `landings/PLAN-LB-166.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-166-manifest-no-push-always-wins` (from the sender)
- [x] epic.md narrative reconciled: the "no push" Open Defect marked shipped; L3-1 recorded as a Watch (BACKLOG under the focus rule)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 (minor, not staged).** The reconcile backfill is a second path that can re-add a push-only step to a local-only plan. It predates this landing and fails open on no observed input. Recorded as a Watch under BACKLOG; a plan would be one change in `manage-execution-manifest.py`, which the operator can ask for.
- **L3-2 to L3-4, documentation duplication.** Minor; recorded, not staged.
