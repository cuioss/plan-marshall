# Landing Analysis: PLAN-LB-156 — Maven root aggregator test-artifact ladder

epic: live-blockers
workstream: WS-02
pr: #1998 (https://github.com/cuioss/plan-marshall/pull/1998)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-156.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-156-maven-root-aggregator-test-artifact-ladder`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `740fe2fdcafacd5936ac58445f43bbdf9654aa80` (queue merge, base `main`), branch
`fix/lb-156-maven-root-aggregator-test-artifact-ladder`. Message `rb-lb-156-maven-root-aggregator-test-artifact-ladder-001.md`
carries `total_tokens=unknown` (out of scope under the standing ruling, no defect).

## Deliverable Fidelity vs Spec

Corroborated with the CI abstraction (`ci pr view`: `merged`, merge commit as stated, head branch as stated) and a read of
`_maven_cmd_discover.py` on `origin/main` (lines 457-550 of the merged file).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `_add_reactor_test_canonicals` emits `package` / `package -DskipTests` when a member consumes a reactor test artifact, `test` / `test-compile` otherwise, reusing the ladder's detection | shipped-as-specified | merged `_maven_cmd_discover.py:480-520`: third parameter `reactor_consumes_test_artifact` picks the pair; `_reactor_consumes_test_artifact` (`:457-477`) reads `metadata.reactor_test_artifacts`, the field `_reactor_test_artifacts` (`:523-550`) fills for the per-module ladder, so the root and a member share one detection (re-read) |
| D2 tests: no consumer, classifier consumer, `test-jar` consumer, nested aggregator, single-module root; `test-jar` question settled | shipped-as-specified | lane reports six new tests plus a fixture-root test and a mutation-after red run of four failures; test bodies not re-read here. The settled answer (a `test-jar` dependency resolves at `test-compile` through `target/test-classes`, only a classifier needs `package`, and the root still switches on both because the ladder's detection includes both) is the lane's reading of the measured record in `standards/maven-impl.md`; not re-read |

Standing constraints re-read at the merged code: the absent-when-no-test-file rule holds (`:510-511`), the nested-aggregator case is left
unchanged (`:514-515`, project-root test), and no change under `.plan/orchestrator/` is reported.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the change is a single-function switch in one script plus tests and two prose
files, and the one place a defect could hide (the function and its detection helper) was read in full on the merged tree. The reading is
by reading: no build, no test run. What only a run could show is tagged `not shown by reading`.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | Hypothesis: a root `pom` aggregator gets `test` / `test-compile` with no test-artifact check | checked | confirms | spec line cite `:454-482` at base; the merged function is the changed form of that block |
| L1-2 | Hypothesis: the per-module ladder uses `package` for a consumer that is not the root | checked | confirms | lane report; the merged `_reactor_test_artifacts` docstring states the same rule (`:523-530`) |
| L1-3 | Hypothesis: a `test-jar`-type dependency needs no `package` and only the classifier form does | checked | confirms as Maven behaviour, no effect on the outcome | lane cites `maven-impl.md` measured record (Maven 3.9.16); the shared detection includes both forms by design (`:548-549`), so D1's "cannot disagree" outranks saving a phase |

**Layer 1 verdict:** no refuting finding. The spec premises held.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_maven_cmd_discover.py:457-520` | mutation-after: four tests red against the base behaviour (lane log `python-2026-11-16-113429.log`) | `SKILL.md` and `standards/maven-impl.md` are outside the spec's Expected Surface; the lane names them as same-module prose that states the contract D1 changes | checked |
| D2 | `test/plan-marshall/build-maven/test_discover_modules.py` | the same four failures are the new tests | none | not re-read |

- **L2-1 (info):** the lane widened the declared surface by the two build-maven prose files. They document the changed rule and belong to the same module; no objection.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_maven_cmd_discover.py:457-477` | a reactor whose only consuming member has `packaging: pom` | root takes `package` where `test` would do: one extra phase, the safe direction | info (the lane documented it) |
| L3-2 | `_maven_cmd_discover.py:516-517` | a reactor where the root's `package` run executes nothing (an `activeByDefault` profile Maven switches off at run time) | a `package` `module-tests` canonical can report green with nothing run, because the `package` ladder is not held to the zero-test guard; the same holds for the per-module ladder shipped earlier | minor, filed as issue #2000 by the lane |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (the lane reports 28956 tests on
the merge head), and the mutation-after red run. No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-2 is a pre-existing gate-truth limit that this plan neither introduced nor widened beyond
adding one more `package` canonical; the lane raised it as issue #2000.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only, no version history | conforms | the merged docstrings (`:457-509`) state present behaviour |
| `pm-dev-python:python-core` | explicit typing, single-purpose helpers | conforms | `_reactor_consumes_test_artifact(known: dict[str, dict], reactor_paths: set[str]) -> bool` |
| `plan-marshall:persona-module-tester` | matched controls, tests that can fail | conforms | the lane's control test (no consumer keeps `test`) and mutation-after run |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: one guard-log R1 refusal (a piped shell listing, replaced with file tools); one wrongly-typed executor notation; one argparse
  rejection on a `ci` call. None changed state. Thirteen routed builds, all `daemon_longpoll`, no fallback. One `module-tests` job hit the
  daemon's learned supervisory bound (775 s, `timeout_source: learned`) and was re-issued with the resolved budget, then passed (798 s).
  `executor-skew` answered `not_applicable` (source checkout).

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed `bd8962d6d`, raised one Major inline finding (the `package` row bypasses the zero-test guard), answered and tracked rather than changed because the fix alters the guard's contract for every `package` canonical including the shipped per-module ladder the spec leaves untouched; the follow-up is issue #2000. Two further claims in CodeRabbit's reply were correct and fixed in `f5531c6fa`; the re-review of that head raised nothing. Sourcery (optional) refused on quota. `review-gate` answered `merge_allowed: true`, `all_handled`. Not independently re-run here.
- CI/merge: green per the lane on every pushed head; queue merge; no rebase conflicts reported.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-153, -154 and -155 on disjoint surfaces; no collision reported.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-156 --status shipped`
- [x] row `pr` stamped — `1998`
- [x] row `landing` stamped — `landings/PLAN-LB-156.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-156-maven-root-aggregator-test-artifact-ladder` (from the sender)
- [x] `epic.md` narrative: one Watch for issue #2000
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- No executor regeneration is owed (no verb or flag added). A harness sync is owed for the edited build-maven bundle source.

## Follow-Ups

- **Issue #2000 (package-phase `module-tests` is not held to the zero-test guard)** — recorded as a Watch; nothing staged. It is a gate-truth
  limit (a false green with nothing run) on the root row and the per-module ladder alike. Whether a plan carries it is the operator's word;
  the live-blockers focus rule puts it at "not blocking" unless the operator rules otherwise.
- **CodeRabbit nits left unfixed** (a cost paragraph that repeats a list, one wording) — recorded here, no plan.
