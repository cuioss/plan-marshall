# Landing Analysis: PLAN-LB-130 — the freshness gate reads the positional tokens of a build row by its tool

epic: live-blockers
workstream: WS-01
pr: #1949 (merge commit `549e35374b66c573d301808c12caedba6c49000d`, one parent `652d977cf`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent, seven files, +707/-39 — `build-maven/SKILL.md`, `_maven_execute.py`, `manage-tasks/SKILL.md`, `_freshness_crosscheck.py`, a new `maven-all-skipped-summary.log` test fixture, `test_maven_execute.py` and `test_freshness_notation_crosscheck.py`. The facts block (`pr=#1949`, `merge_state=merged`, `deliverables 3/3`) agrees with git. `total_tokens=unknown` is an unobserved fact, not a defect.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — positional tokens are module scope only for the tool whose positionals are modules | shipped-modified | `parse_row_scope` (`_freshness_crosscheck.py:835-861`) reads the row's own `notation`: Maven/Gradle/npm rows keep `payload[0]` and drop the remaining positionals; any other notation with more than one positional returns `None`. Re-read. **Beyond the spec:** a `:`-prefixed payload token on a Maven/Gradle row returns `None` (849-850), a Gradle submodule carve-out the spec said it did not change, and an npm exemption. See L2-1 and L3-1. |
| D2 — remedy hint only for a row an executor flag broke | shipped-as-specified | `row_scope_remedy_hint` and `_EXECUTOR_RUN_FLAGS` (leaf, not re-read), pinned to the argparse declarations by a test (leaf). |
| D3 — report credit counts executed, not skipped | shipped-modified | `_report_executed_tests` (`_maven_execute.py:425-445`) returns `tests - skipped`, clamped at 0, and credits nothing for an absent or unparseable `skipped`. Re-read. Extended beyond the spec to the summary path of `apply_zero_test_guard` (614-625), with a new fixture log. The time bound the spec froze is unchanged (re-read 536-553). |
| Optional cosmetic: render dropped goals in `row_scopes` | not implemented, by design | It would contradict the Done-when's pinned `row_scopes`. Recorded as an unmet optional, not a miss. |

Files no deliverable names, each explained: the `maven-all-skipped-summary.log` fixture (the summary-path extension), `manage-tasks/SKILL.md` (documents the notation-keyed reading) and `build-maven/SKILL.md` (documents the executed-count rule). The spec's Expected Surface names two fixture files (`_pre_commit_verify_freshness_fixtures.py`, `_freshness_notation_crosscheck_fixtures.py`) that needed no change (leaf, not re-read), and the landing correctly left them alone.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the two sibling landings drained in the same scan.
- **Verdict:** layer 1 findings (2, minor); layer 2 findings (2: 1 major, 1 minor); layer 3 findings (5: 1 major, 4 minor) plus one point not shown by reading. The major is one defect seen on two layers (L2-1, L3-1).

Re-read at `_freshness_crosscheck.py` 366-378, 795-861, 1360-1392 and 1470-1505; `_gradle_cmd_discover.py` 486-525; `_maven_execute.py` 416-445, 536-553 and 596-645; `build-maven/SKILL.md:40`; `_maven_cmd_parse.py` 472-483. **Not re-read** (unverified leads): the base-side behaviour the leaf compares against (the claim "at base this row was fresh"), the test lines (`test_freshness_notation_crosscheck.py` 1183-1198, 1389-1430, 1487, 1509, 1600; `test_maven_execute.py` 981-1071), `manage-tasks/SKILL.md` 405 and 626, `_EXECUTOR_RUN_FLAGS` against the argparse declarations, the emission path of `ROW_ARGS_UNREADABLE`, and `_npm_cmd_discover.py`.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's own rule for an unknown or absent notation (more than one positional returns `None`) loosens the gate for a NARROW change: `module-tests plan-marshall` with no notation was a narrow refutation at base and is an inability that can pass now. This conflicts with the spec's "never more permissive" constraint. Edge case, because the dispatch boundary always stamps a notation. | checked (code re-read; base side not re-read) | refutes | `_freshness_crosscheck.py:852-853` |
| L1-2 | The spec's premise that an unreadable row refuses every whole-tree change holds. | checked | confirms | `_freshness_crosscheck.py:1386-1392` |
| — | The spec's premise that a single Gradle `:mod:test` row read as canonical-unknown with no scope at base holds. | checked (leaf) | confirms | `_freshness_crosscheck.py:852` |

**Layer 1 verdict:** findings — 1 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_freshness_crosscheck.py:835-861` | the four Done-when rows and the gate-level npm row (leaf: lines 1389-1430) | the Gradle carve-out and npm exemption (L2-1, L2-2) | checked |
| D2 | `_freshness_crosscheck.py:927` (leaf) | leaf: the `module-tests -k foo` case | none | checked |
| D3 | `_maven_execute.py:425-445, 549-552` | leaf: `test_maven_execute.py` 981-1071 | the summary-path extension | checked |

- **L2-1 (major):** the Gradle carve-out is not in the spec and contradicts two of its lines. The spec says the goal-positional tools must NOT return `None` (that would refuse every whole-tree change, "the same false red by another route") and that a single `:mod:test` row is "not changed here". The merged code returns `None` for any `:`-prefixed payload token on a Maven or Gradle row (`_freshness_crosscheck.py:849-850`), and the Gradle discoverer prefixes EVERY submodule task that way (`_gradle_cmd_discover.py:492-498`). Consequence in L3-1.
- **L2-2 (minor):** the npm exemption covers a row no discoverer emits, so the test that pins it (`run :check --workspace=pkg-a`, leaf, not re-read) breaks the spec constraint "a row shape is one a discoverer emits".

The lane's narrative says the Gradle row was "flipped from fail-open to unreadable". That is true only relative to an intermediate commit. Against the base `652d977cf` a single-task submodule row went from passing to refused, and a multi-task one from narrow to unreadable.

**Layer 2 verdict:** findings — 2 (1 major, 1 minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_freshness_crosscheck.py:849-850, 1392` | a whole-tree change, ledger at the current sha = a root `build` row plus any submodule row (`:core:test`) | Gradle canonicals are outside the vocabulary, so a Gradle ledger stays `UNDETERMINED`, and `_unreadable_scope_blocks_whole_tree` refuses when ANY candidate parses to `None`. At base this ledger was two inabilities and passed; now it is `stale` (`build_scope_unreadable_for_whole_tree_change`). A root-only re-run at the same sha cannot clear it, because the submodule row stays a candidate. A ledger of submodule rows alone is a correct refusal. Gradle consumers only; this repository (pyproject) is unaffected. | major |
| L3-2 | `build-maven/SKILL.md:40` | — | the sentence lists "a report whose population it cannot read proves nothing either way" among the shapes that keep their green, yet the same sentence and `_maven_execute.py:626-638` make a leading `test` run with no summary and no executed report `indeterminate` | minor |
| L3-3 | `_maven_cmd_parse.py:476-479` | a `-Dtest` selector that matches an all-`@Disabled` class | the comment calls the run "a truthful green", while `apply_zero_test_guard` (614-625) now makes a measured collected-but-none-executed run `indeterminate` | minor |
| L3-4 | `_freshness_crosscheck.py:373` (token), emission not re-read | a Gradle `:module:` row or an unknown-notation multi-positional row that DOES carry `--command-args` | per the leaf, `row_scopes` renders `unreadable: args_carry_no_command_args`, a false cause; the `REASON_SCOPE_UNREADABLE` docstring omits both new causes | minor (unverified lead) |
| L3-5 | `manage-tasks/SKILL.md:626` (not re-read), `_freshness_crosscheck.py:849` | a Gradle submodule row | the documented remedy (re-dispatch a build whose argv carries no flag) cannot be carried out; and the inline literal `'plan-marshall:build-npm:npm'` at 849 sits beside the named `_GOAL_POSITIONAL_NOTATIONS` and `_PYPROJECT_NOTATION` constants | minor |

**Layer 3 not shown by reading:**

- An UNMEASURED Maven summary with collected tests still credits even if every counted line is all-skipped; whether a quiet log can show that line cannot be settled by reading.
- Whether any other freshness test module carries a multi-positional row under a non-pyproject notation (the lane's own hypothesis; a content sweep was not possible).
- Whether `plan_context` sets `PLAN_MARSHALL_HOME`, and whether the suite is green at the merge commit.
- npm standalone ` --prefix=dir` rows and Maven profile rows carry unknown flags and parse to `None` at base too; untouched by this landing.

**Layer 3 verdict:** findings — 5 (1 major, 4 minor); not shown by reading — 4

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec D1 | goal-positional tools must NOT return None | deviates | `_freshness_crosscheck.py:849-850` |
| spec D1 observed note | a Gradle submodule row is not changed here | deviates | the carve-out is pinned by `test_freshness_notation_crosscheck.py:1183-1198` (leaf, not re-read) |
| spec constraint | never more permissive | deviates | `_freshness_crosscheck.py:852-853` (unknown notation) and the multi-task submodule rows |
| spec constraint | key on the row's own notation | conforms | `_freshness_crosscheck.py:835-853` reads `entry['notation']` only |
| spec D3 | the time bound is unchanged | conforms | `_maven_execute.py:539-550` |
| spec constraint | tests use rows a discoverer emits | deviates | the npm colon-script test (L2-2) |
| CLAUDE.md § Documentation Standards | current state only, no version history | conforms | the SKILL.md edits (leaf); but see L3-2 for accuracy |
| ref-code-quality | named constants over magic literals | deviates | `_freshness_crosscheck.py:849` |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` `missing_keys: [total_tokens]` is no defect.
- Anomalies: 24 build submissions, six verify and module-tests heads; four runs failed on machine-level `ENOSPC` in `/tmp` while other sessions' suites ran (the inode exhaustion PLAN-LB-141 has since addressed in the test harnesses). Two CodeRabbit quota refusals, two 90-minute waits and an escalation to `@coderabbitai full review`. Two guard refusals, both the lane's own (`R7` a main-checkout edit, `R1` a piped command), and three read-only `grep` diagnostics over build logs, which the lane reports itself.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `919b58b19`, `c696cdd88`, `19419dd9f` and the final head `2625b1160` ("No actionable comments"). Ten findings (eight inline, two nitpicks), each fixed by a pushed commit. Sourcery (optional) refused on quota. Review numbers re-read with `runbook_lane review-gate --pr-number 1949` on the fixed code: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 10 (agrees). `review_body_findings_handled` is **not re-verified** (no progress file was passed to the re-read).
- CI/merge: green at every head that reached the PR; merge-queue squash with one parent.
- Sonar: `n/a`, consistent with a project without Sonar.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-130 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-130 --field pr --value 1949`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-130 --field landing --value landings/PLAN-LB-130.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-130 --field plan_marshall_plan_id --value rb-lb-130-freshness-gate-scope-by-notation`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- **L3-1 is reported to the operator at once and is not staged.** A fix plan is staged only on the operator's word. It would narrow the carve-out so a submodule row never refuses a whole-tree change by itself (read the module from the `:module:` token, or treat the row as an inability like a root row), and would drop or re-justify the npm exemption. It would touch `_freshness_crosscheck.py`, `manage-tasks/SKILL.md` and `test_freshness_notation_crosscheck.py`.
- Minors L1-1, L2-2 and L3-2 to L3-5: held on the Watch as the minors of the PLAN-LB-130 landing.
