# Landing Analysis: PLAN-LB-127 — CodeRabbit concerns raised only in its summary are filed, the file-limit notice is recognised, and the dormant cuioss-review-bot is removed

epic: live-blockers
workstream: WS-03
pr: #1941 (https://github.com/cuioss/plan-marshall/pull/1941)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `e71329548ee23996c20f651dcefa18d508cb45c4`, a merge-queue squash with ONE parent `bbe421f15bbcc0e9b1eb8fa181829c7f96c3e3ef`
> (the PLAN-LB-125 squash), read with git before the leaf prompt named it; 107 files, +1387/-6199. `ci pr view` reports `state: merged`
> with that merge commit. Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is
> `complete: false`, `missing_keys`: `total_tokens` (out of scope) and four review-and-Sonar numbers (`unresolved_review_threads`,
> `review_body_findings_total`, `review_body_findings_handled`, `sonar_open_new_issues`), which this lane's text could not emit before
> PLAN-LB-116 added them; the four are an Open Defect. The lane's review history, CI and merge-queue claims were not re-read; the merge
> state and merge commit were. CodeRabbit never reviewed this PR (107 files, over the cap of 100); the operator accepted the gap in the lane.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a summary-only concern is filed | shipped-modified | the summary marker, the two headings and the four-string veto are data in `coderabbit.md:66-78` and the conjunction in `github_pr.py:308-344`; the positive test uses an assembled body (nitpick section inside a summary); the live #1931 shape, a free-text Merge Risk concern, is still dropped (L3-2) |
| D2 the file-limit notice is a structural refusal | shipped-as-specified | both wordings in `refusal_patterns` and `refusal_size_patterns`, both cap regexes (`coderabbit.md:84-99`, re-read); the cap returns 100, not the file count, for both wordings; the red test at `bbe421f15` and the two controls are present |
| D3 the documents and guards state the new rules | shipped-modified | the contract, `coderabbit.md` and `findings-pipeline.md` carry the rule; the prose says the summary that strays is filed (`coderabbit.md:154-156`, re-read), which the code does not do for a free-text concern; history wording remains (L2-3) |
| D4 `cuioss-review-bot` removed completely | shipped-modified | target package, standard, publish workflow, registrations and tests deleted; one tombstone constant remains (`_config_defaults.py:881`); the migration strips the name in memory but does not save it in the `noop` state (L3-1) |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`, the resolved `orchestrator.analyze` level). One leaf per landing, as the dispatch rule requires. The orchestrator re-read the points marked "re-read" below at their `file:line`; points not listed there are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the conjunction logic, the migration and a 107-file sweep is the depth the Dispatch Decision Rule exists for, and its reading must not share context with the PLAN-LB-116 landing.
- **Verdict:** layer 1 findings (1); layer 2 findings (3 minor); layer 3 findings (**2 major**, minors). One major falsely blocks a consumer's merge gate after the upgrade, the other leaves the D1 fail-open in place for the live summary shape.

### Layer 1 — Specified

The spec's D1 premise, "the veto names the concern sections the reproduced body carries", cannot be met by data alone: the only live body it cites (#1931) carries its concern as free text in the Merge Risk block, which `coderabbit.md:147-148` says every summary carries. The spec's own verify-first clause says D1 is closed as not reproducible when no live body can be cited; the lane cited one and then built the positive fixture from a different, assembled shape. D2 and D4 premises hold.

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | a section-title veto can express the live concern the spec cites | checked | refutes | `_github_pr_fixtures.py:461-483` (re-read: the fixture puts a nitpick section inside the summary and says the live concern is a Merge Risk statement) |

**Layer 1 verdict:** findings — 1 (the premise gap behind L3-2).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `github_pr.py:308-344`, `coderabbit.md:66-78` | `test_a_summary_that_carries_only_a_concern_files_one_finding` (red at `bbe421f15`) | the live shape is untested | checked |
| D2 | `coderabbit.md:84-99` | `test_the_commanded_notice_is_counted_as_a_size_refusal` (red at `bbe421f15`) | none | checked |
| D3 | contract, `coderabbit.md`, `findings-pipeline.md` | the population guard suite | history wording (L2-3) | checked |
| D4 | `upgrade.py:430-454`, `_config_defaults.py:881` | the two pure-function migration tests | no test runs the save path (L3-1) | checked |

- **L2-1 (minor):** the skip-notice control checks nothing D1 changed. `test_the_skip_notice_summary_still_files_nothing` (`test_comments_stage_filters.py:421-433`, re-read) uses the `no-new-commits` reply, which has no summary marker, is a registry refusal caught before the noise filter, and asserts `count_skipped_noise == 0`. The spec wanted the skip-notice summary to keep its `count_skipped_noise`. The case D1 does change, a draft, ignored-path or label skip notice that carries the marker, is untested and is now filed as a `pr-comment` finding where it used to be dropped.
- **L2-2 (minor):** the D4 sweep missed the PR-Agent AGENTS.md rationale (`tools-sync-agents-file.md:83` and four more places; unverified leads).
- **L2-3 (minor):** history wording in docs and a test docstring: "lost those concerns whole", "it used to be an unconditional drop, and it is now filed" (`coderabbit.md:150,162`, re-read), `bot-participation-contract.md:1089`, and a stale "files nothing at HEAD" docstring.
- **Lane claim 9 (no surface drift):** the out-of-surface files each carry a withdrawn-bot or walkthrough statement the diff corrects; no unexplained file was found. The deleted `test_pr_agent_contentless_*` modules carried drop-path currency arms; whether a CodeRabbit equivalent exists is `not shown by reading`.

**Layer 2 verdict:** findings — 3 (minor).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `upgrade.py:446-454`, `532` (re-read) | a consumer `marshal.json` with no legacy `enabled_bots` and `required_bots: cuioss-review-bot,coderabbit`, which is the previous `STANDARD_REQUIRED_BOTS` seed (read at `bbe421f15`), so every config seeded or back-filled before this landing has it | `migrate_bot_lists` strips the name in memory and returns `state: noop`; `cmd_migrate_bot_lists` saves only when the state is not `noop`; the tool reports `removed_retired` and leaves the file unchanged, so the roster still names an unregistered bot, which classifies `unregistered_kind` and blocks every merge for that consumer. Not this repository (its own merges passed). The tests call the pure function and never the save path | **major** |
| L3-2 | `github_pr.py:332-344`, `552-554` (re-read) | a CodeRabbit summary with the summary marker, `## Walkthrough`, and a concern written as free text in its Merge Risk block, none of the four section titles | the conjunction holds and no veto string is present, so the body is dropped as noise; the bot resolves `participated_but_empty`; the D1 fail-open persists for the live shape; the docs say a straying summary is filed (`coderabbit.md:154-156`) | **major** |
| L3-3 | `github_pr.py:552` (re-read) | a body carrying `No actionable comments were generated` and a `Nitpick comments` section | the sentence is an unconditional `ignore_patterns` drop evaluated before the concern check; live co-occurrence is not shown, the code path is | minor |
| L3-4 | `coderabbit.md:77-78` | the historical "Outside diff range comments" wording | the two veto strings have no fixture provenance and the case-sensitive substring misses that wording | minor |
| L3-5 | `github_pr.py:341` | a draft, ignored-path or label skip notice that carries the marker | now filed as a `pr-comment` finding in normal use (fail-closed toward filing, but a new false positive); a walkthrough that merely quotes "Follow-ups" is filed the same way | minor |
| L3-6 | `upgrade.py:438` | an answer naming only the retired kind | saved as `required_bots=''`, zero required reviewers, reported only through `removed_retired` | minor |

**Layer 3 not shown by reading:** whether CodeRabbit really publishes `No actionable comments were generated` beside a nitpick section; whether the live concern is also posted as a formal review body (which would make L3-2 a duplicate-channel loss rather than a lost concern); whether the full suite is green.

**Layer 3 verdict:** findings — 2 major, 4 minor. Both majors are recorded as Open Defects and reported to the operator; neither is staged.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only, no history | deviates | `coderabbit.md:150,162` (re-read), `bot-participation-contract.md:1089` |
| spec standing constraint | fail closed toward filing | deviates | L3-2, L3-3 |
| spec standing constraint | a consumer configuration naming the bot is migrated | deviates | L3-1 |
| spec standing constraint | data, not code; `REFUSAL_LAYERS` and stage order unchanged | conforms | the `github_pr.py` and `_github_pr.py` diffs are comments only |
| spec standing constraint | `refusal_patterns` never unioned with `ignore_patterns` | conforms | separate lists, pinned by `test_bot_registry_patterns.py` |
| spec standing constraint | single tombstone literal | conforms | `_config_defaults.py:881` |
| spec standing constraint | no executor regeneration | conforms | no `.plan/execute-script.py` in the diff |

## Metrics and Anomalies

- Tokens: `unknown` (not measured; out of scope per the focus rule).
- Anomalies: `self-review: budget-exhausted` (two rounds; NEW-1, NEW-4 and NEW-7 left open by decision, NEW-1 being the D1 evidence boundary this analysis refutes); three builds waited on queue admission (up to 1764 s); the lane broke its own rule with `git grep` for several enumeration passes and reported it.

## Routing and Merge Behavior

- Review: CodeRabbit (required) refused for size ("This PR contains 107 files, which is 7 over the limit of 100") and rate-limited on the commanded review; Sourcery (optional) refused for size. No review exists on any head, so the standing review authorization did not apply; the operator chose "Record the gap and merge" in the lane (lane's claim, not re-read).
- CI/merge: merge queue; `ci pr view` reports merged with the merge commit above (re-read). `verify` green on the merge head (lane's claim, not re-read).
- Sonar: `n/a` (Sonar is not enabled for this project).
- Collision: PLAN-LB-116 ran in parallel with two shared files (the operator accepted the overlap at emit); no conflict or re-verify signal is reported.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1941`
- [x] row `landing` stamped `landings/PLAN-LB-127.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-127-coderabbit-registry-summary-concerns-and-file-limit`
- [x] epic.md narrative reconciled (landing entry, the incomplete-landing Open Defect, two HIGH Open Defects, one Watch)
- [x] PLAN-LB-41 D1 and D5 retire now that D4 merged (recorded on the parked row's annotation)
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 and L3-2 (majors)** are Open Defects in epic.md and were reported to the operator in the same turn. A fix plan only on the operator's word. L3-1 qualifies under the stop rule (a consumer's merge gate falsely blocks after the upgrade); L3-2 qualifies if the live concern is not also posted through a formal review (not shown by reading). If staged, L2-1, L3-3 and L3-6 are fold candidates.
- The four missing landing numbers: an Open Defect naming the message and the keys (the lifecycle producer gap PLAN-LB-116 L1-1 names).
- The remaining minors and the history wording: one Watch; not staged.
- Owed outside the plan, operator-run: a harness sync.
