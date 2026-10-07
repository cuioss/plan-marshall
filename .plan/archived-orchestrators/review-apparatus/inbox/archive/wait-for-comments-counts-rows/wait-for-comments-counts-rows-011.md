envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:45:24Z

# Outline over-declares scripts and under-declares doc contracts, and the counts cancel

component: plan-marshall:phase-3-outline
category: anti-pattern
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

`solution_outline.md` declared 13 affected files. The merged squash commit touched 12. A count
comparison reads as a near-perfect match. The set comparison does not:

- **5 declared, never touched** — all of them SCRIPTS:
  `automatic-review/scripts/bot_registry.py`, `automatic-review/scripts/review_completeness.py`,
  `workflow-integration-github/scripts/github_pr.py`,
  `workflow-integration-github/scripts/github_re_review.py`,
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py`.
- **4 touched, never declared** — all of them DOC CONTRACTS:
  `tools-integration-ci/standards/api-contract.md`,
  `tools-integration-ci/standards/blocking-wait-pattern.md`,
  `tools-integration-ci/standards/pr-review-operations.md`,
  `workflow-pr-doctor/standards/automated-review-lifecycle.md`.

Nine of thirteen declarations were individually wrong; the two errors have opposite sign and nearly
cancel in the aggregate. The whole fix landed in `_github_pr.py` + `github_ops.py` plus three test
files.

This is a **recurrence** of the already-recorded "plans under-scope the doc contract surface"
archetype, now paired with its mirror image: over-scoping the script surface.

## Root cause

Outline-time scope estimation reasons about where a behaviour *conceptually* lives (the bot registry,
the completeness checker, the re-review path — all plausibly related to a re-review detector) rather
than about where the single predicate actually sits. The doc-contract half is the complementary
blind spot: the standards that DESCRIBE a changed CLI/predicate contract are downstream of the code
change and are only discovered while implementing.

## Proposed action

- Make the outline's `Affected files:` declaration carry two explicitly separated lists —
  **implementation surface** and **contract/doc surface** — so an empty doc-surface list is visibly a
  claim ("this change alters no documented contract") rather than an omission.
- When a deliverable modifies a CLI flag set, a predicate contract, or a returned-field schema,
  require the outline to enumerate the standards documents that state that contract. The
  `ext-self-review-plan-marshall` contract-source detector already surfaces these candidates at
  self-review time — pull the same detector forward to outline time.
- Grade declared-vs-realized by SET agreement (Jaccard / precision + recall), never by count
  agreement. A count-only comparison scored this plan as ~92% accurate; set agreement scores it 8/17
  ≈ 47%.

## Evidence

- aspect: request_result_alignment — `outline_declared: 13, realized: 12, intersection: 8, outline_recall_pct: 61.5`, with the 5 over- and 4 under-declared files enumerated.
- aspect: artifact_consistency — `affected_files_exact_match` returned `warn` with `outline_only[13]` and forwarded to the manifest aspect.
- `references.json` `affected_files` (7 entries) achieved 100% recall — the narrower, later-written list was accurate; the wider outline list was not.
