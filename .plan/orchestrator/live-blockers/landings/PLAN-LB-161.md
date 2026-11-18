# Landing Analysis: PLAN-LB-161 — Clear the Dependabot alert on the `zod` pin in the build-npm workspace fixture

epic: live-blockers
workstream: WS-04
pr: #2014 (https://github.com/cuioss/plan-marshall/pull/2014)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-161-zod-fixture-dependabot-alert-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

Merge commit `aeead84bcda2956ba94d0a00421fdccc4999cbce` (squash, one parent `b296b4726b73db5494c4ad96cdd9a57cad48d8b3`, the PLAN-LB-160 merge), read with git; PR #2014 `merged`, merge-group run `44257145835` `success`, read through the CI abstraction. The diff is one file and one line.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `zod` declared at a range whose lowest version is 4.6.6 or later; nothing else changed; the `build-npm` suite passes unchanged | shipped-as-specified | `git diff aeead84^1 aeead84` is the single hunk `"zod": "^3.22.0"` → `"zod": "^4.6.6"` in `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json:7`; no test, lockfile or other fixture touched. The suite result (34,123 tests, `verify` green on three heads) is the lane's claim and was not re-run; the merge-group run is `success`. |

The spec's one HYPOTHESIS (no code reads the `zod` range) is confirmed by the lane and by the layer-3 reading below. The Expected Surface (one path) matches the diff exactly: no surface drift.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`), and the orchestrator re-read the load-bearing `checked` points at their lines before writing them here. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with PLAN-LB-160's, which was read in its own leaf in the same drain.
- **Verdict:** layer 1 findings (one minor, one not shown by reading); layer 2 findings (one minor imprecision, one not shown by reading); layer 3 clean (two points not shown by reading).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | `^4.6.6` has a lowest version of exactly 4.6.6 and admits nothing below it | checked | confirms | `packages/api/package.json:7` |
| L1-2 | The OBSERVED premises hold at the merge: five tracked fixture files, no lockfile, `zod` only in the manifest and one docstring | checked | confirms | `test_npm_derivation_resolver.py:162` |
| L1-3 | The spec names the `build-npm` suite as the fixture's consumer, but `test/plan-marshall/manage-architecture/test_native_resolver_graph_impact.py` also loads the same workspace (`NPM_FIXTURE`, `:68`) and asserts graph edges and impact on it | checked (the `NPM_FIXTURE` use re-read; that its assertions read names only is the leaf's reading, not re-read) | refutes (premise incomplete, harmless) | `test_native_resolver_graph_impact.py:68` |
| L1-4 | The advisory data (GHSA-mrhx-c7xc-m3w5, vulnerable `< 4.6.6`, first patched 4.6.6) and the existence of `zod` 4.6.6 on the registry | not_shown_by_reading | none | read from the GitHub alert on 2026-11-17, not from the repository |

**Layer 1 verdict:** findings — 1 (L1-3, minor); not shown by reading — 1 (L1-4)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | the one-line hunk at `packages/api/package.json:7` | none; the deliverable carries no "fails at" clause and is a data change in a fixture, so no test can fail on it by design | none; the lane's line claims `_npm_cmd_discover.py:315-318` and `extension.py:223` are correct (re-read at `_npm_cmd_discover.py` `_extract_dependencies`) | checked |
| the lane's mechanism wording | — | — | the lane and the spec say the range is read "only to decide it names no workspace module"; at the merge the range is never read at all, because discovery keeps the names and drops the values before the join (`_extract_dependencies` appends `name:runtime` / `name:dev`; `_name_edge_join.py:196` splits on `:`, re-read). The conclusion holds; the stated mechanism is imprecise (minor) | checked |
| the lane's test claims | — | — | that the `build-npm` suite passes, and whether CI ran the heavy `verify` for a `.json`-only change under the footprint gate (`skip-on-docs-only`, `extra-buildable` names no `test/**/*.json`), cannot be shown by reading | not_shown_by_reading |

**Layer 2 verdict:** findings — 1 (the mechanism wording, minor); not shown by reading — 1

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| none | — | — | — | — |

No code at the merge reads or compares the `zod` range (`_name_edge_join.py:196` keeps the name only; no semver or range parsing exists in `build-npm/scripts/`), so a 4.x major cannot break a fixture consumer by reading. Dependabot version updates are configured for `github-actions` and `pip` only (`.github/dependabot.yml`, read whole), so no version-update PR will target this fixture.

**Layer 3 not shown by reading:** L3-1: whether the alert closes, and whether a later 4.x advisory opens one, depends on GitHub's dependency graph, which no file in the repository shows. L3-2: how the external `dependency-review` workflow judged `^4.6.6` (its rules are external to the repository, and this analysis did not read that check's result on #2014).

**Layer 3 verdict:** clean — not shown by reading — 2

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec Standing Constraints | One manifest line, no test edited, no lockfile, no other fixture | conforms | `git diff --name-status`: one `M`, one line |
| CLAUDE.md § Tests and fixtures | A fixture is data, no logic | conforms | the hunk is one JSON value |
| CLAUDE.md § Commit Trailer | A commit ends with the `plan-marshall` trailer | conforms | squash `aeead84` ends with `Co-authored-by: plan-marshall <noreply@cuioss.de>` (the leaf's reading; trailer keys are case-insensitive) |
| spec Standing Constraints | No install, no network call by the plan | not_shown_by_reading | the diff carries no install artifact, which is consistent and not proof; the lane's self-review sub-agent disclosed one read-only npm registry GET |

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none; out of scope under the ruling of 2026-10-23, so no defect.
- Duration: not stated by the lane.
- Anomalies: the lane charged itself with one breach — it posted `@coderabbitai review` on `751ee8d01` before reading the `review_complete_after_handling` predicate (the reply was `no_unreviewed_commit`) — and escalated to `@coderabbitai full review` on the operator's selection, outside its documented condition. Neither is checked here: the session store was not read. A parallel target-generation flake in `test_target_tree_foundational_skill_freshness.py` (`plugin.json missing for: plan-marshall`) failed one full `module-tests` run's exit code with `failed 0`, and passed in the next scoped run and every `verify`; the lane read it as a flake outside this plan's surface. The lane's `{guard_log}` has no line for its session, so no guard refusal was recorded (`.plan/temp/guard.log` was not re-read here).

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 0 body findings, 0 handled. `runbook_lane review-gate --pr-number 2014` on the merged head returns `unresolved_review_threads: 0`, `review_body_findings_total: 0`, `merge_allowed: true`, `reason: all_handled`. All three numbers agree. CodeRabbit's check ended `NEUTRAL` / skipping on the final head, while the gate accepted a qualifying review; the lane records that CodeRabbit's `unchanged_files_carry_forward` marker is not accepted by the gate's finished-review predicate and that this cost one operator question — a recurring-signal Watch below.
- CI/merge: merged through the merge queue (`aeead84`, merge-group run `success`). The base was merged into the branch before the last head, as the lane states.
- Sonar: `sonar_open_new_issues: n/a` — Sonar is not enabled for this project (ruling of 2026-10-28), so no figure was collected or required.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-161 --status shipped`
- [x] row `pr` stamped — `2014`
- [x] row `landing` stamped — `landings/PLAN-LB-161.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-161-zod-fixture-dependabot-alert` (from the sender)
- [x] epic.md narrative reconciled against the queue rows
- [x] two Watches opened (the review-gate predicate and the target-generation flake); no Open Defect
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **The Dependabot alert is closed.** Read from the API after this analysis: alert 1 is `state: fixed`, `fixed_at` 2026-11-18T07:41:57Z (before the landing message, 07:43:32Z), not dismissed. The analysis above could not show it from the repository, which is why L3-1 stays `not_shown_by_reading`; the closure was established by the later API read. Whether Dependabot should ignore or group test fixtures stays the operator's call, and this landing adds a datum: version updates are configured for `github-actions` and `pip` only, so the alert came from the dependency graph and not from a version-update setting.
- **L1-3 (minor, not staged).** The spec under-enumerated a second consumer of the fixture; harmless because it reads names only.
- **Watches** — see the epic's `## Watches` for the `review-gate` carry-forward marker and the target-generation flake.
