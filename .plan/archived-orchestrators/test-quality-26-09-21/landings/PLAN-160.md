# Landing Analysis: PLAN-160 — Sweep the three single-instance defect classes

epic: test-quality
workstream: WS-03
pr: [#1486](https://github.com/cuioss/plan-marshall/pull/1486) — merged via merge queue, squash `f21a0dc66aab7c59191664575d5680bfd8f5b9a0`

> Landing record for one shipped plan. Written by `analyze` after verifying claims against
> ground truth. Drained from inbox message
> `sweep-the-three-single-instance-defect-classes-014.md` (`landing-check`: `complete: true`,
> `missing_keys: []`), corroborated against the real PR state and the real merge commit.

## Deliverable Fidelity vs Spec

**The spec carried 5 deliverables; the plan shipped 8.** The growth is legible and was
productive — R1/R3/R4/R5 each split a survey from its remediation, and D6 (arm the mechanical
checks) plus D7 (port the rules into the standard) are the "ship the check, not the sweep
output" obligation the spec's D4 stated as a requirement rather than as its own deliverable.
No deliverable was dropped.

| Deliverable (shipped) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 — survey cross-slice filename pins, re-express by role (R1) | shipped | 87-file diff; `test/test_harness_shape_guards.py` (485 new lines) arms the regression check |
| 2 — survey hand-kept mirrors, convert or decline on merits (R3) | shipped **swept-only, by design** | The spec permitted a merits-based decline; R3 admits no mechanical predicate and gained no ported rule. Correctly reported as swept-only rather than claimed as checked. |
| 3 — survey conditional teardown (R4) | shipped | `test_pollution_guard_scoping.py` +129 |
| 4 — survey runtime-derived parametrize bindings (R5) | shipped | The R5 I folded in at the 2026-09-13 drain |
| 5 — evaluate the project-wide `empty_parameter_set_mark` flip, adopt-or-decline | shipped, **verdict: ADOPT** | `pyproject.toml:170` now carries `empty_parameter_set_mark = "fail_at_collect"` — verified in the tree. This discharges the evaluate-and-verdict condition R5 carried. |
| 6 — arm mechanical shape-regression checks | shipped | `test/_shared/_test_shape_scan.py` + `test/test_harness_shape_guards.py` — both verified present at HEAD |
| 7 — port the R1/R4/R5 rules into the testing-methodology standard | shipped | `testing-methodology.md:603` now names `fail_at_collect` — verified |
| 8 — report each class's population, verdicts and check status | shipped | — |

⚠️ **The instrument this plan built is itself defective — see Follow-Ups.** The deliverables
landed; the thing they landed has the epic's own defect class inside it.

## Metrics and Anomalies

- **Tokens**: 9,380,546 (`record-metrics`) — **3.75x** the 2.5M error anchor.
- **Duration**: 6h17m worked, **21h25m wall** — 7.1x the 180-minute anchor.
- **Second consecutive double-threshold breach.** PLAN-165 was the first.
- ⛔ **Two sources disagree on every phase total for this run.** `record-metrics` reports
  9,380,546 tokens (finalize 5,270,710 / execute 2,689,773); the `plan_efficiency` aspect
  reports 9,882,263 (5,441,503 / 3,072,253). The finalize-over-execute ratio is **1.96x** or
  **1.77x** depending on which you read. The conclusion is robust to the disagreement — both
  are far above 1.0 — but the disagreement is unexplained and is recorded rather than smoothed.
- ⛔ **THE FINALIZE-COST RETIREMENT IS NOW REFUTED TWICE.** PLAN-155 retired that watch on a
  third consecutive sub-1.0 ratio. PLAN-165 ran 2.85x; this run ran 1.96x/1.77x. Three points
  retired it; two have since refuted it. **The watch stays re-opened** and the relocated
  `settled.md` item must be read with both beside it.
- **Where the WALL time went is a different answer from where the tokens went**: 68.1% of
  16,009,410 ms of script wall time sits in two CI-polling notations, against 24.2% in the
  build wrapper. The verification was cheap; the review and CI round-trips were not.
- `loop_back_iteration: 5`, with `pre-submission-self-review` at `firing_count: 7`.

## Routing and Merge Behavior

- **Review**: 17 findings triaged and fixed across two rounds (CodeRabbit +
  cuioss-review-bot); the review retrospective compared 3 reviewers over 12 actionable
  comments. ⛔ **At least ten of those findings were defects in this plan's own new scanners**,
  every one found by review rather than by the author or by the guards' own tests.
- **CI/merge**: all checks green; merged through the GitHub merge queue. Unlike PLAN-165 the
  queue path worked unaided here — `branch-cleanup` recorded "rebase deferred to queue,
  queue-merged, corroborated".
- **Operator-reported tooling defect**: `ci pr view --plan-id` returned `auth_failed`
  consistently after worktree removal while `--project-dir` succeeded. Recorded as an Open
  Defect — the `--plan-id` fallback path is the suspect, and the post-cleanup state is the
  same systematic condition the footprint resolvers fail in.
- **Header artefact, not a discrepancy**: the run banner printed `PR #n/a` while the
  `landing-facts` block carries `pr=#1486`. The machine-readable fact is correct; the header
  field was empty at print time because the branch was already cleaned up.

## Declaration Form — the first severe UNDER-declaration this epic has measured

| Quantity | Value |
|---|---|
| Declared entries (`corpus surfaces`) | **21** |
| Realized files (`git show --stat f21a0dc66`) | **87** |
| Realized files INSIDE the declared surface | **28** |
| Realized files OUTSIDE it | **59** |
| Coverage | **32.2%** |

Of the 59 outside, **42 are under `test/plan-marshall/`** — sibling directories the spec did
not name — plus 5 under `marketplace/bundles/`, 4 under `test/marketplace/`, and the three
new root-level test modules.

⛔ **This is the dangerous direction.** Every prior measurement in this epic was either
accurate (PLAN-155, 97 of 97) or over-declaring (PLAN-165 and plan-06, which cost throughput
and manufactured a false collision). Under-declaration is the class that admits genuinely
colliding plans, and at 32.2% this spec's declaration would have supported almost no true
disjointness verdict. The gate passed PLAN-160 as disjoint on a surface that covered a third
of what it touched.

⚠️ **Consequence for PLAN-140**: its surface is `derived` — explicitly the union of other
plans' surfaces, PLAN-160's among them. A derivation from a 32%-accurate declaration is not
a reliable input. PLAN-140 was already `indeterminate` and sequenced; this is a second,
independent reason not to size it from the ledger.

## Reconciliation Actions

- [x] row `status` → `shipped` — `queue --transition PLAN-160 --status shipped`
- [x] row `pr` stamped `#1486`
- [x] row `landing` stamped `landings/PLAN-160.md`
- [x] row `plan_marshall_plan_id` already stamped at launch
- [x] 14 inbox messages drained (13 candidate-lessons + this landing), each with a recorded disposition
- [x] **PLAN-175 staged** — `queue --add-row`, spec present, surface `declarative` (4 entries)
- [x] Open Defects opened: the shape-scanner defect family; the metrics disagreement; `ci pr view --plan-id` auth_failed post-cleanup; the 32.2% under-declaration
- [x] `resume_anchor` updated; both generated blocks regenerated

## Follow-Ups

- **PLAN-175 — harden the shipped shape scanners** (staged, WS-03). The three families from
  candidate-lessons -008/-009/-010: recognizers enumerated from examples rather than from the
  construct (5 findings, two of them the *same gap found twice* because the first fix
  enumerated one more spelling); guards credited with a property their predicate does not
  entail, or entails about the wrong subject (4 findings — one is a vacuity guard that is
  itself vacuous); and asymmetric path normalization (1, silent in the over-reporting
  direction). **This epic's thesis defect, located inside the instrument built to prevent it.**
- **6 candidate-lessons promoted** (`2026-09-14-05-001` … `-006`).
- **4 folded onto existing corpus lessons** as recurrences: the post-merge footprint anchor
  (**third** occurrence — and it refutes the resolver-parity remedy recorded one drain ago as
  *sufficient*: this run measured both failure directions at once, 0 paths and 130 paths
  against a true 87, so the correct anchor is the merge base or the merged commit); the
  finalize re-firing cost (second); the TOON transcript round-trip; and the argparse-rejection
  family (**fourth** — this one fired inside the lessons-capture Signal Gate itself, the step
  whose job is to notice recurrences).
- **The will-INVALIDATE category is new and unnamed.** Candidate-lesson -012: D5's project-wide
  default flip made `testing-methodology.md:581` false — a file the plan never opened, whose
  content its change invalidated. A declared surface distinguishes *will-modify* from
  *will-read*; it has no way to express this. No diff-scoped review can catch it, because the
  diff and the now-wrong sentence are in different files and the sentence did not change.
  The doc was fixed in-plan after a review bot found it (`testing-methodology.md:603` verified).
