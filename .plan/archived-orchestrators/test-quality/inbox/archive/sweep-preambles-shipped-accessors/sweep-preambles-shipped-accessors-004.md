envelope_version=1
sender_type=plan
sender_id=sweep-preambles-shipped-accessors
epic=test-quality
kind=landing
created=2026-09-08T01:53:51Z

# Landing: PLAN-135 — Sweep the preambles the shipped accessors can now reach

plan_id: sweep-preambles-shipped-accessors
epic: test-quality
workstream: WS-02
outcome: merged
pr: 1446
merge_commit: b64db66713d037b456d3c0c0956c68839208b173
base_sha_at_merge: 64733323a47cda18771661db81f62c1eb3a6aad6

## Measured result

| Rule | Before | After |
|------|-------:|------:|
| `test-module-preamble-boilerplate` | 103 | **13** |
| — `spec_from_file_location` shape | 61 | 13 |
| — `Path(__file__)` parent-chain shape | 42 | **0** |
| `subprocess-pythonpath` | 17 | **5** |

The 13 residual is the **structural floor**, derived not asserted: 11 sites across 4
classes no shipped accessor can reach, plus the 2 `test/conftest.py` occurrences this
plan never edits. The 5 remaining `subprocess-pythonpath` rows are all confirmed rule
false positives, each filed as a finding for WS-03; none suppressed, no assertion
weakened.

Collected tests 25237 green (compile, lint, test). This plan added and removed no test —
the count moved only because upstream #1443 and #1444 landed during the run.
`KNOWN_REGISTRATION_COLLISIONS` unchanged at 17 names; loader-contract unresolved-ratio
bounds still describe the tree (86/736 = 11.68%, inside [10%, 14%]). No guard constant
was adjusted to fit the result.

Footprint: 89 files, +689 / -1194 (net -505). No `marketplace/bundles/**` file, no
`test/conftest.py` edit — both explicit spec exclusions, held.

## Where the spec's premises were wrong

Three corrections the run derived and the epic should carry forward:

1. **The structural floor is 11 sites across 4 classes, not 8 across 3.** The fourth
   class is a test loading a *test-tree sibling*
   (`test_analyze_target_scope.py:293`), which the `(bundle, skill, file)` accessor
   signature cannot name either. The expected residual is therefore 13, not 9.
2. **`test/conftest.py` carries 2 occurrences, not 1** (lines 580 and 1178).
3. **`subprocess-pythonpath` false positives are FIVE, not six.** D1's own prose said
   six while its remedy table enumerated five; the prose was corrected in place.

The spec also predicted the loader-contract guard file would need editing. It did not:
TASK-005 measured both bounds as already describing the tree and correctly made no edit.
Upstream had meanwhile refactored the absolute `UNRESOLVED_CALL_SITE_BOUND` into a ratio
pair, so the constant's shape changed — but not by this plan.

## Review

CodeRabbit raised one Major functional-correctness finding no local gate caught
(`test_staleness_guard.py:712` — the `_run_python` child was not isolated from the
repository, weakening a negative control). Fixed in TASK-8; re-review at the fix head
returned no actionable comments and merge risk dropped Moderate -> Low.
Its stated remedy was over-broad and was declined with measurement: "assert the package
import fails" yields `blocked=marketplace`, which would have destroyed the matched
negative control. The isolation half was taken, the assertion half was not, and
CodeRabbit agreed with that scoping in-thread.

`cuioss-review-bot` reviewed the same diff and reported clean. `sourcery` never reviewed
(hard quota, ~7 days).

## Open items handed to WS-03

- 5 `subprocess-pythonpath` rule false positives: `462a76`, `c0f4ef`, `02c9ea`, `79bf95`,
  `24970a`. The rule matches a call SHAPE and cannot see a deliberate env scrub, a
  helper-supplied `PYTHONPATH`, or a `-m` stdlib invocation.
- `a073b5` — no test discriminates whether the `_run_python` isolation holds. The code is
  correct and the prose accurate, but both consuming assertions pass under the old and new
  regimes, so a regression would keep them green. Missing regression protection, not a
  live defect.
- `a0fdec` / lesson `2026-09-07-21-001` — `baseline-reconcile` scrapes localized
  `git merge-tree` prose without pinning `LC_ALL`, reporting 8 conflicts for 2 real ones.
  It drove an entire wasted drift-recovery cycle in this run. Outside this plan's declared
  footprint (`marketplace/bundles/**`), so filed rather than fixed.

## Process cost worth the epic's attention

Two `baseline_drift` aborts at the phase-5 entry gate cost 296,505 tokens for no work.
The second was structural, not bad luck: the documented recovery re-dispatches `2-refine`,
which resolves drift as CONTENT and never advances the branch, while the gate tests git
ANCESTRY. Recorded as inbox candidate-lesson 001. The hand-merge that cleared it left a
merge commit that then broke `finalize-step-sync-baseline`'s rebase — the two steps
interact and neither documents it.

Run totals: 4h42m worked / 11h44m wall / 5.8M tokens, against a 3.5M error anchor.
