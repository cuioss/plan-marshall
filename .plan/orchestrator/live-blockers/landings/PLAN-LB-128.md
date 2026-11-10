# Landing Analysis: PLAN-LB-128 — The retired-bot roster strip is saved, and a CodeRabbit summary that carries a free-text concern is filed

epic: live-blockers
workstream: WS-03
pr: #1946

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-128.md`. Written by the
> `analyze` verb from the inbox message `rb-lb-128-coderabbit-roster-save-and-summary-concern-001.md`
> (runbook lane, `opencode` harness, `deepseek-v4.1-flash/high`) after verifying claims against ground
> truth. Merge commit `af1ad9513207ac81035c1351be288e0bb23fe405`, a squash commit with ONE parent,
> `b2652750a66c79a2abc3af7468559a775067f79e` (the PLAN-LB-126 ledger land, read with git before the leaf
> prompt named it). The spec base `9cd644892` and that parent differ only under `.plan/orchestrator/`
> (`git diff --stat 9cd644892 b2652750a -- marketplace test` is empty), so the lane's reverted-run base is the
> spec's stated base.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the strip is saved; an emptied required list re-seeds CodeRabbit | shipped-as-specified | `upgrade.py:512-515` returns `retired_stripped` when `removed_retired` is non-empty; the unchanged save condition covers it. Re-seed `upgrade.py:485-493`: `coderabbit`, provenance `migrated`, `optional_bots` de-duplicated, `reseeded_required: true`; an operator-written `''` is excluded by `required_was_non_empty` (`:476`). Tests `test_verb_saves_a_strip_when_no_legacy_key_remains` and `test_a_strip_that_empties_required_reseeds_coderabbit` assert the persisted file, the state and (for the first) a byte-identical second run |
| D1 — the `ImportError` fallback is read and reported | shipped-modified | Reported as `retired_kinds_unavailable` in the returned dict (`upgrade.py:504-505`), not removed. Met at report level only: nothing outside `upgrade.py` and one test names the key (content search), so no router shows it. See L2-1 |
| D2 — a Merge Risk concern is filed; a clean verdict does not swallow a section | shipped-modified | Two data fields in `coderabbit.md:80-84`, accessors `bot_registry.py:811-839`, `_section_texts_after_heading` / `_concern_sections_are_clean` at `github_pr.py:324-381` wired into `_is_contentless_boilerplate`; the `ignore_patterns` drop is vetoed by the actionable markers and by a concern section. The section boundary DEVIATES from the spec text (see L1-1) and is the stricter reading |
| D2 — skip notices | shipped-as-specified | `## Review skipped` is a contentless heading (`coderabbit.md:74`, data only); the file-limit refusal is classified before the filter and stays a counted refusal |
| Surface | added-unplanned (8 files) | 18 files touched against 10 declared entries (two of them conditional). Undeclared: `automatic-review/SKILL.md`, `bot-participation-contract.md`, `marshall-steward/SKILL.md`, four `test_bot_participation_contract_*.py`, `test_bot_registry_markers.py`. The leaf found each forced by a pin or a statement the change made false; no unexplained file |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved through
`orchestrator.analyze`, `[DISPATCH]` record written by the resolve), and the orchestrator re-read the points
named below at their `file:line` before writing them here. The reading is **by reading, no build, no test run,
no write**: what only a run could show is tagged `not shown by reading`.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code across 18 files and ten lane claims is the depth the dispatch rule exists for, and this landing's read must not share context with any other.
- **Re-read by the orchestrator:** `github_pr.py:324-381` (lines 336, 337, 349, 371, 379), `upgrade.py:420-528` (476, 487-493, 504-515), `bot_registry.py:811-839`, `upgrade-flow.md:486-500`, `coderabbit.md:66-90`, `test_comments_stage_filters.py:458-598`, `test_legacy_bot_list_migration.py:436-524`, three content searches (the key `retired_kinds_unavailable`, the #1946 comment id, the marker `final_review_risk_start`), and the diff surface. **Not re-read** (the leaf's reading stands as an unverified lead): the fixtures file's block shape, `bot-participation-contract.md:1089`, `marshall-steward/SKILL.md`, the `_cmd_sync_defaults` body, and the guard tests at `test_legacy_bot_list_migration.py:553-590`.
- **Verdict:** layer 1 findings — 2 (minor); layer 2 findings — 2 (minor); layer 3 findings — 5 (minor). No blocker, no major.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's literal section boundary (next heading, `<details>` or `<!--`) is unworkable on the captured shape: the text after `<strong>Merge Risk:</strong>` reaches `<!-- final_review_risk_start -->` before the verdict sentence, so under the literal rule both the clean and the concern block lack the verdict and the spec's own hold-at-base control (clean wording stored 0) would turn into a filing. The lane's deviation (strip closed comments first, bound at heading, `<details>`, `</details>`) is the stricter, fail-closed reading | checked (deviation and fail-closed arm re-read; the marker's presence in the fixtures confirmed by search; the block structure itself not re-read) | confirms | `github_pr.py:336-338,346-350` |
| L1-2 | D2(c) "each of these fails at `9cd644892`" cannot hold for the file-limit control: that notice is a registered refusal classified before the noise filter at base too. The lane's evidence note is correct | checked | confirms | `test_comments_stage_filters.py:629` (leaf), `coderabbit.md:74` |
| — | Base equivalence; "stored 0, noise 1 at base" is consistent for D2(a); Hypothesis 3 (no `noop` pin for a strip, no re-introduction by backfill) holds in the parts read | checked (base equivalence re-run by the orchestrator; the rest the leaf's reading) | confirms | `git diff --stat 9cd644892 b2652750a -- marketplace test` empty |
| — | Hypothesis 2 (the #1931 concern also posted through a formal review) | not_shown_by_reading — the leaf does not fetch third-party text; the lane reports it **refuted** (14 formal reviews carry two review-body summaries, neither states the concern). Recorded as the lane's unverified claim | none | — |

**Layer 1 verdict:** findings — 2 (both about the spec's text, neither changes the outcome)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 (a) | `upgrade.py:512-515` | `test_verb_saves_a_strip_when_no_legacy_key_remains` (`:436-478`) asserts state, `removed_retired`, the persisted `coderabbit` and the byte-identical second run; at base the state is `noop` and nothing is saved | none | checked |
| D1 (b) | `upgrade.py:485-493` | `test_a_strip_that_empties_required_reseeds_coderabbit` (`:480-515`) asserts `reseeded_required`, persisted `coderabbit` and provenance `migrated` | none | checked |
| D1 fallback | `upgrade.py:504-505` | `test_a_degraded_retired_bot_tombstone_is_reported` (leaf: simulates the import failure by patching two module attributes, not the import path) | the report key is read by no consumer (L2-1) | checked |
| D2 (a)/(b) | `github_pr.py:324-381`, `bot_registry.py:811-839`, `coderabbit.md:80-84` | the concern test, the nitpick-swallow test (`:540-562`), the Merge Risk-swallow test (`:564-582`), the empty-verdicts test (`:500-517`), the verdict-outside-the-block test (`:519-538`) each discriminate their stated mutation | none | checked |
| D2 (c) | `coderabbit.md:74` | the constructed skip-notice test: `participated_bots == []` does not discriminate (uncredited at base too); only stored 0 / noise 1 do (leaf, not re-read) | none | checked |

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L2-1 | The `ImportError` fallback is "read and reported" only in the returned dict. `retired_kinds_unavailable` is named by no document and read by no consumer (content search: `upgrade.py` and one test only), so the operator never sees it; a degraded strip still saves nothing and the consumer stays blocked | checked | refutes | `upgrade.py:504-505`; search |
| L2-2 | The lane says the second clean wording (#1946) is "OBSERVED verbatim in `_github_pr_fixtures.py` / the registry". It is in the registry only (`coderabbit.md:84`; the comment id appears nowhere else), and its control body (`test_comments_stage_filters.py:476-498`) is hand-built and not labelled CONSTRUCTED, against the spec's fixture rule | checked | refutes | `test_comments_stage_filters.py:484-491`; search |

Not shown by reading: every `mutation-after` job id and its red/green outcome (lane claims; `/home/oliver/.plan-marshall/marshalld/job-logs/` was not opened).

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `github_pr.py:379` | a Merge Risk block that carries a declared clean literal AND a concern in a following sentence, e.g. "No merge-blocking risk was found. The contract test can pass after the verdict list is lost; fix in a follow-up." | the clean test is a substring test, so the section reads clean and the summary drops as noise: the concern is lost (fail open). Accepted on purpose for the #1946 wording (`coderabbit.md:84`) and pinned by `test_comments_stage_filters.py:476-498`; the spec text ("contains none of") prescribes containment | minor |
| L3-2 | `github_pr.py:370-375` | CodeRabbit renders the heading as `<strong>Merge Risk</strong>:` or `Merge risk:` | the heading literal is case-sensitive and exact; no section is found, the loop adds none, the function returns clean and the concern-bearing summary drops again — the pre-fix defect, with no drift signal. The verdict side fails closed; the heading side does not | minor |
| L3-3 | `github_pr.py:346-349` | "Merge Risk: Low. The contract test is unpinned. Merge Risk: Minimal. No actionable merge-blocking risk remains." with no heading line or `<details>` between the two | the scan resumes at `end`, the next boundary, so the second occurrence is absorbed into the first section, which then contains the verdict: clean, concern dropped. "Judge every occurrence" holds only across a boundary. Unlikely on the observed shape, where each block sits in its own `<details>` | minor |
| L3-4 | `bot_registry.py:824-825` | a registry typo `concern_section_headings: "Merge Risk:"` (a scalar, not a list) | reads as `[]`, which disables the concern veto silently: one character restores the #1931 drop. The same typo on `clean_section_verdicts` (`:838-839`) reads `[]` and fails closed, so the two fields are asymmetric | minor |
| L3-5 | `upgrade-flow.md:493-494` (and `marshall-steward/SKILL.md:454-455`, not re-read) | the sentence "because a project is never left with no required reviewer" | false for the case the code deliberately preserves: an operator-written `required_bots: ''` stays empty (`upgrade.py:476,487`; test `:553`). The accurate statement is that the strip never empties the required list | minor |

Not defects (re-read): the re-seed is correct on its edge cases (`required_was_non_empty` is computed on `strip()` before the strip; a
whitespace-only value is never re-seeded; retired names only in `optional_bots` never re-seed; the second run strips nothing and is `noop`;
the save is the pre-existing `save_config` with its concurrent-modification refusal). An unclosed `<!--` anywhere in a CodeRabbit body
returns `None` before the heading is searched (`github_pr.py:336-338`) and counts as not clean: an extra filing, the documented
fail-closed direction. Only `coderabbit.md` declares the two new fields, so every other bot keeps its old behaviour, and the GitLab
producer has its own `_is_obvious_noise` without the registry.

**Layer 3 not shown by reading:** whether the runbook-lane `review-gate` parser matches CodeRabbit's `<picture>`-decorated section title
(`Nitpick comments: 1`) — the lane's own residue, not this merge's code; the producer here matches `Nitpick comments` as a substring
(`github_pr.py:638`, leaf), so the same gap is not reproduced in the merged code.

**Layer 3 verdict:** findings — 5 (all minor; none fails open on an observed shape, so the stop rule stages nothing). Reported to the operator in the turn that recorded them.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current behaviour only, no timestamps or versions | deviates (minor) | `bot-participation-contract.md:1089` keeps a past-tense rationale (leaf; not re-read); the rest of the diff conforms |
| CLAUDE.md § Script Execution | executor regeneration only if a verb or flag is added | conforms | no argparse change in `upgrade.py` or `github_pr.py` |
| spec | fixture body is a captured live shape or labelled CONSTRUCTED | deviates | `test_comments_stage_filters.py:476-498` (L2-2) |
| spec | fail closed toward filing | deviates | L3-1 to L3-4 |
| spec | CodeRabbit stays the required reviewer; the migration never leaves a project with no required reviewer | conforms for the strip; the document wording overstates it (L3-5) | `upgrade.py:487-493` |
| spec | data, not code; `REFUSAL_LAYERS` and stage order unchanged; `refusal_patterns` not unioned | conforms | `coderabbit.md:80-84`; no `_github_pr.py` change |
| memory | no Sonar, no token or measurement work | conforms | the diff touches neither |

## Metrics and Anomalies

- Tokens: `total_tokens=unknown` (OpenCode measured none; out of scope under the operator ruling of 2026-10-23). The inbox check reports `complete: false` on that key alone, so no Open Defect is opened.
- Duration: not supplied. 27 routed builds, all `daemon_longpoll`; no launch fault, no `degraded`, no killed job (lane claim).
- Anomalies: one `verify` failed only in the unrelated target-tree generation precondition (`[Errno 39] Directory not empty`) and passed on re-run (lane claim); self-review reached its 3-round limit (`budget-exhausted`) and the operator chose to proceed.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `227604f18`; one review-body nitpick, fixed in `020de0249`; re-triggers at `020de0249` and `b6fdb064d` were refused for quota and the standing authorization applied (lane claim; not re-read from the provider). Sourcery (optional) refused for its own budget.
  `runbook_lane review-gate --pr-number 1946` re-run on the merged head by the orchestrator: `unresolved_review_threads: 0`, `review_body_findings_total: 0`, `review_body_findings_handled: 0`, `merge_allowed: true`. These agree with the landing's three numbers. They are the same parser's output, and the lane itself records that the live review body carried one nitpick that this parser did not count, so the agreement does not establish the body count. `review_body_findings_handled` is **not re-verified** (the progress file was not opened).
- CI/merge: PR #1946 is `merged`, merge commit `af1ad9513`, via the merge queue (squash, one parent). `ci pr view` agrees with the landing's `pr` and `merge_state`.
- Sonar: `n/a` (not enabled for this project); consistent with the landing.
- Collision: the lane reports none. PLAN-LB-132 (`github_pr.py`) stays sequenced after this plan, which has now shipped.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-128 --status shipped`
- [x] row `pr` stamped — `1946`
- [x] row `landing` stamped — `landings/PLAN-LB-128.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-128-coderabbit-roster-save-and-summary-concern` (the sender, not typed)
- [x] epic.md narrative reconciled: queue annotation for PLAN-LB-128; the two PLAN-LB-127 HIGH Open Defects retired on the merge; the PLAN-LB-116 and 127 minors Watch narrowed; a new Watch for the PLAN-LB-128 minors
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- The five layer-3 minors and the two layer-2 minors are a Watch, not staged (stop rule: none fails open on an observed shape). L3-2 and L3-4 together are the cheapest fail-open to close and could ride PLAN-LB-132, which edits `github_pr.py` next; that is the operator's call.
- The lane's residue about the `review-gate` parser and a `<picture>`-decorated title belongs to PLAN-LB-129 (running). Its spec already covers the `Nitpick comments: N` count form; whether the `<picture>` decoration is also covered is not stated there. Recorded as a Watch on PLAN-LB-129; its spec is not edited.
- Operator-run, owed: a harness sync for the `marketplace/bundles/` edits (the lane does not run it). No verb or flag was added, so no executor regeneration is owed for this landing.
