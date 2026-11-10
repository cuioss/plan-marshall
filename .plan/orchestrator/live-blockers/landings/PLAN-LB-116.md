# Landing Analysis: PLAN-LB-116 — The runbook lane cannot merge past an unhandled review finding or an open Sonar issue, and its landing claims are checkable

epic: live-blockers
workstream: WS-04
pr: #1940 (https://github.com/cuioss/plan-marshall/pull/1940)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `5eb2f9d9d2c112e34f676260672cc1ee6b9be902`, a merge-queue squash with ONE parent `e71329548ee23996c20f651dcefa18d508cb45c4`
> (the PLAN-LB-127 squash), read with git before the leaf prompt named it; 19 files, +2407/-207. `ci pr view` reports `state: merged` with that
> merge commit. Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is
> `complete: false`, `missing_keys: total_tokens` (out of scope per the focus rule). The lane's review history, CI, the merge-queue run and the
> per-head test runs were not re-read; the merge state and merge commit were.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `review-gate` decides the review half of the merge gate | shipped-modified | the verb exists with the six reasons and a fixture per case (`runbook_lane.py:2721-2851`; `test_runbook_lane_review_gate.py`, including the unresolved-threads-only stub test); § 6 step 5 and § 7 state the rule; the resolved-thread check tests the last comment only (L3-1), an unrecognised surface can drain as zero findings (L3-2), the dispositions are CLI flags and are not read from the progress file, and head currency stays prose |
| D2 the landing carries the review and Sonar numbers | shipped-as-specified | four keys added to `LANDING_REQUIRED_KEYS` (`_orchestrator_inbox.py:1389-1407`), rejected under the same schema version, `n/a` legal only at the Sonar key; one fixture per key in `TestReviewAndSonarNumbers`; `analyze.md` carries the re-read and false-claim step. The lifecycle producer cannot emit the four keys (L1-1) |
| D3 `sonar-gate` accepts no lane dismissal, and the read covers hotspots and a paging total | shipped-as-specified | `--dismissed-keys` refused as `lane_dismissal_not_accepted` (`runbook_lane.py:2060-2071`); hotspot leg with `TO_REVIEW`, an `undecidable` answer on a missing or short total (`sonar.py:1098-1120`); fixtures for the hotspot-only head, the short page and `not_configured` |
| D4 the lane reads its mailbox | shipped-as-specified | `resolve` publishes `inbox_read_command` (`runbook_lane.py:2932-2935`); the flags exist in `orchestrator.py` and a test parses them through the orchestrator's own argparse |
| D5 an evidence claim needs an artifact | shipped-as-specified | the `not evidenced` rule is stated once in § 1 and § 8 refers to it; two text tests pin it |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`, the resolved `orchestrator.analyze` level). One leaf per landing, as the dispatch rule requires; the 127 landing was read by its own leaf. The orchestrator re-read the points marked "re-read" below at their `file:line`; points not listed there are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the merged review-gate parser and the Sonar read is the depth the Dispatch Decision Rule exists for, and its reading must not share context with the PLAN-LB-127 landing.
- **Verdict:** layer 1 findings (1 minor, 1 info after re-grading); layer 2 findings (3 minor); layer 3 findings (**1 major**, minors). The major fails open on the case D1 exists for.

### Layer 1 — Specified

The premises hold. Two points: D2 makes four keys REQUIRED while the lifecycle producer (`phase-6-finalize` emit-landing) has no source for any of them, and D1 says a disposition is "in the progress file" while the verb takes it as a flag.

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | the four required keys do not make every other producer incomplete | checked | refutes | `_orchestrator_inbox.py:1389-1407` (re-read); the lane names it in `emit-landing.md` and `landing-payload-spec.md` |
| L1-2 | D1 reads the dispositions from the progress file | checked | refutes | `runbook_lane.py:2849` takes `--disposition` values and never opens the progress file (re-read); `sonar-gate` has the witness check, `review-gate` does not |

L1-1 is graded **minor** here, below the leaf's major: it is a producer gap the lane names as owed, and it gates nothing. Every lifecycle-emitted landing now reads `complete: false` and the drain records an Open Defect for it until the finalize steps publish the numbers. L1-2 is a spec wording the lane did not meet (the operator rule is mechanical for Sonar, prose for the review dispositions).

**Layer 1 verdict:** findings — 2 (both minor).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `runbook_lane.py:2721-2851` | `test_runbook_lane_review_gate.py` (stub-red parametrize) | lane claim 2 "an unrecognised surface stops the gate" refuted for three shapes (L3-2) | checked |
| D2 | `_orchestrator_inbox.py:1389-1407` | `TestReviewAndSonarNumbers` | none | checked |
| D3 | `runbook_lane.py:2060-2071`, `sonar.py:1098-1120` | `test_runbook_lane_sonar.py`, `test_read_open_issues.py` | none | checked |
| D4 | `runbook_lane.py:2932-2935` | the mailbox-command parse test | none | checked |
| D5 | SKILL.md § 1, § 8 | the two text tests | none | checked |

- **L2-1 (minor):** the lane's residue says `_count_section_findings` "over-counts only". It under-counts: a section with no declared `(N)` whose nested per-file summaries also carry no count returns 1 whatever the number of nested findings (`runbook_lane.py:2441-2459`, re-read). Two nitpicks under one heading read as one, so one disposition clears the section.
- **L2-2 (minor):** `review-gate` never witnesses the disposition lines; the operator rule for Sonar is checked against the progress file and the review rule is not (`runbook_lane.py:2849`, re-read).
- **L2-3 (minor):** `_SECTION_DEPTH` is dead, and its comment states a depth rule `_enclosing_sections` rejects; one test docstring states the same dead rule (`runbook_lane.py:2387`, unverified lead).
- **Surface:** `plan-spec.md` and `test_plan_spec_template_contract.py` (D3 operator rule), `test_sonar_analysis_revision.py` (D3 hotspot leg), `emit-landing.md`, `landing-payload-spec.md`, the plan-orchestrator `SKILL.md` (D2) and the Sonar `SKILL.md` (D3) are outside the declared surface and each is explained by a deliverable. No unexplained file.

**Layer 2 verdict:** findings — 3 (minor).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runbook_lane.py:2617-2630` (re-read) | a resolved thread `[bot opener, lane "fixed in abc", bot "This still applies", lane "done"]` | `_thread_concern_remains` tests only `thread[-1]`, and only when a bot wrote it; the last comment is the lane's, so the thread reads handled and `merge_allowed` is true with the bot's restated concern open. The spec says the thread's last BOT comment. This is the resolve-to-silence shape D1 exists to refuse | **major** |
| L3-2 | `runbook_lane.py:2516-2521`, `2778` (re-read) | a review body that is prose only; a counted summary with no section keyword (`Potential issues (2)`); a finding posted as an `issue_comment` | the title with no keyword is skipped, a prose body parses to 0, and `issue_comment` records are accepted and never parsed; with no open thread `merge_allowed` is true over findings never read | minor |
| L3-3 | `runbook_lane.py:2315-2323` (re-read) | a bot saying "still persists", "has not been addressed", "not yet addressed" | the marker vocabulary is a bare substring list with no negation handling; these phrasings fail open, and the generic "not addressed" refuses a thread whose bot confirmed a fix and named another item | minor |
| L3-4 | `runbook_lane.py:2407-2409` (re-read) | a disposition `finding: coderabbit nitpick nitpick-1 — TBD` | the evidence is any non-blank text, so `TBD`, `-` and `n/a` are accepted as a sha or reason | minor |
| L3-5 | `runbook_lane.py:2468-2475` | an edited or reordered review body | finding ids are positional (`{section}-{n}`), so a disposition binds to a position, not to content | minor |
| L3-6 | `runbook_lane.py:2839-2851` (re-read) | a read taken while a re-review is pending | head currency is prose only; the verb never compares a review's commit with the head | minor |
| L3-7 | `runbook_lane.py:2010-2022` | `--hotspot-keys ''` beside a selected hotspot key | the hotspot partition is trusted from the lane, so the key is admitted as an issue dismissal; needs an operator selection of that key | minor |
| L3-8 | `runbook_lane.py:1879-1897`, SKILL.md:744 | the documentation | a docstring says `None` where the code returns `set()`; the gate command names a `{hotspot_keys}` placeholder the Sonar read does not publish | minor |

**Layer 3 not shown by reading:** whether the Sonar provider accepts `ps=500` on the hotspot request and whether the `ci pr comments` TOON round-trip keeps long HTML bodies intact; whether every test passes (only a run shows it).

**Layer 3 verdict:** findings — 1 major, 7 minor. The major is recorded as an Open Defect and reported to the operator; it is not staged.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only, no plan or deliverable labels | deviates | `# D4 —` and `# D5 —` section headers in `test_runbook_lane.py`; "writes none of them yet" in `landing-payload-spec.md`, `emit-landing.md`, `_orchestrator_inbox.py:1385` (re-read) |
| CLAUDE.md § Script Execution | scripts run via the executor | deviates | `analyze.md` and the landing template give a bare `runbook_lane review-gate --pr-number {N}` (unverified lead) |
| spec standing constraint | fail closed throughout | deviates | L3-1, L3-2 |
| spec standing constraint | CI abstraction only | conforms | `_read_review_surfaces` runs the `ci` notation; a test pins the invocation |
| spec standing constraint | standing review authorization never overrides a `false` | conforms | SKILL.md § 7 |
| spec standing constraint | gates are verbs with tests, not prose | conforms | head currency is the stated exception |
| project test rules | isolated `PLAN_MARSHALL_HOME` fixture | not_shown_by_reading | the review-gate and Sonar tests are pure-function or `tmp_path`; the conftest wiring was not read |

## Metrics and Anomalies

- Tokens: `unknown` (not measured; out of scope per the focus rule).
- Anomalies: `self-review: budget-exhausted` (four rounds, one operator-selected fourth round; the round-4 fixes are unverified by a fifth); seven CodeRabbit trigger comments, with CodeRabbit pausing automatic reviews after `e8fb39841` so the last two heads carry no review (the standing review authorization applied); Sourcery refused twice on size; two guard refusals by the lane (R7, R1), both corrected at once; the main checkout's executor predated the `review-gate` verb and was refreshed.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `e8fb39841` and four earlier heads; six reviews carried findings, each answered in-thread and resolved (lane's claim, not re-read). Sourcery (optional) refused on size.
- CI/merge: merge queue; `ci pr view` reports merged with the merge commit above (re-read). The final head ran `verify` green (lane's claim, not re-read).
- Sonar: `n/a` (Sonar is not enabled for this project); the landing's Sonar keys carry `n/a`, consistent with that.
- Collision: PLAN-LB-127 (running in parallel, two shared files with this plan) merged first; no rebase conflict or re-verify signal is reported by either lane.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1940`
- [x] row `landing` stamped `landings/PLAN-LB-116.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-116-runbook-lane-review-and-sonar-gates`
- [x] epic.md narrative reconciled (landing entry, one HIGH Open Defect, one Watch)
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 (major)** is an Open Defect in epic.md and was reported to the operator in the same turn. A fix plan only on the operator's word. If staged, L3-2 to L3-4 and L2-1 are fold candidates (one file, `runbook_lane.py`).
- L1-1 (the lifecycle producer cannot emit the four numbers), the doc-standard deviations and the remaining minors: recorded as one Watch; not staged.
- Owed outside the plan, operator-run: the executor regeneration in every project that runs the lane (a new verb) and the harness sync.
