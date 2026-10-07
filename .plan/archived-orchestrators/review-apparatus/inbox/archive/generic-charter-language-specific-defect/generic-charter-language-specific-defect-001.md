envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T16:48:20Z

# A foreign-repo deliverable reaches done at the commit, and lands nowhere

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_aspects: request_result_alignment, logging_gap_analysis, chat_history_analysis

## Context

Three of this plan's eight deliverables (D6 `cuioss-organization`, D7 `pr-agent-settings`, D8 `API-Sheriff` + `TokenSheriff`) targeted foreign repositories. All three were implemented, committed, and pushed. Tasks 9, 10 and 11 reported `done` at 1/1, 2/2 and 4/4. The host PR #1130 merged, branch-cleanup ran, and the plan advanced to archive.

Verified at retrospective time across all four foreign checkouts: every branch is pushed and in sync with its origin, `git branch -r --contains` reports each commit on its feature branch **only**, and `ci pr list --state open` returns **zero** pull requests for any of the four branches (cuioss-organization has one unrelated open PR #235; API-Sheriff has two unrelated ones). Three deliverables are therefore complete-but-unlanded, in four repositories, with nothing tracking them.

## Root cause

Task done-ness is measured against the local commit. For a host-repo task that is sound, because the plan's own PR carries the commit to main. For a foreign-repo task the commit is the *first* step of landing, not the last, and no step in the plan lifecycle — not the task's own verification command, not any phase-5 gate, not any of the 22 finalize steps — asks whether a foreign change acquired a pull request.

The gap is not an oversight of awareness. The request document carried an explicit `Foreign-repo warning` instructing that each foreign change "land as its own PR in its own repository". Phase 5 then logged the shortfall correctly and repeatedly: the three `[ARTIFACT]` lines for tasks 9, 10 and 11 each end with the literal words **"PR not yet opened."** The fact was observed, correctly worded, and written to the work log three times. Nothing reads `[ARTIFACT]` bodies, so a correctly-logged blocking fact reached the archive without ever reaching a gate.

## Proposed action

1. Add a foreign-landing gate to phase-6-finalize that runs before `archive-plan`: for every deliverable whose declared `affected_files` contains an absolute path outside the project root, resolve the target repository's landing state and refuse to archive while any is `pushed_no_pr`.
2. Give it a deterministic backing verb rather than prose — `ci pr landing-state --project-dir P --branch B` returning one of `merged` / `pr_open` / `pushed_no_pr` / `unpushed`. The four-repository sequence this retrospective ran by hand (`git status --porcelain --branch`, `git branch -r --contains`, `ci pr list`, correlate head branch) is fully deterministic.
3. Make `manage-solution-outline list-deliverables` emit a `foreign: true/false` column per `affected_files` entry, so the gate has a population to iterate and every coverage ratio stops silently mixing 23 host paths with 8 foreign ones.

## Evidence

- aspect: request_result_alignment — D6/D7/D8 status `unlanded`; four foreign repos, zero PRs, commits contained by their feature branch only
- aspect: logging_gap_analysis — three `[ARTIFACT]` lines ending "PR not yet opened."; no finalize step consumes `[ARTIFACT]` bodies
- work.log 2026-08-09T11:35:10Z, 11:40:38Z, 11:45:26Z — the three artifact records
- decision.log 2026-08-09T11:58:05Z — "their deliverables are committed and pushed in four foreign repositories" (committed and pushed; never opened)
- request.md § Dependencies and Sequencing — "land each foreign change as its own PR in its own repository"
