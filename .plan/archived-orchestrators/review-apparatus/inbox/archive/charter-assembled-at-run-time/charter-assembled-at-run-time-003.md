envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:07Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high

# Make the retrospective footprint rename-aware and multi-PR-aware

## Context

For plan `charter-assembled-at-run-time`, the shared footprint resolver answered from the `pr_landing` tier (#1611, 28 files). `check-artifact-consistency` then graded `affected_files_recall` at 36% (`error`). `check-outline-vs-shipped` reported 8 `include_unrealised`, and manifest rule M6 reported 29 declared-but-unrealized paths. Three measurement artifacts account for nearly all of it:

- The D8 pilot landed separately as #1605 (39c945f81), so its 5 files are invisible to a single-PR tier.
- The `pr_agent -> cuioss_review_bot` git renames record only the new path, so the declared deletes of the old paths read as unrealized.
- 25 of 45 declared paths are foreign-repo (`foreign: true`) paths that no tier can ever realize.

## Root cause

The footprint is modelled as one repo, one PR and name-status-free paths. A multi-PR, multi-repo plan with renames therefore grades its own declaration style as an execution failure.

## Proposed action

(a) Resolve the footprint over every PR the plan landed. The status ledger and landing records can supply the PR set. (b) Read rename pairs (`--name-status -M`) and count a declared delete/write of either side as realized. (c) Exclude `foreign: true` declarations from the recall denominator and report them as a separate, explicitly unmeasured population. Never grade them as missing.

## Evidence

- aspect: artifact_consistency: recall 35.6%, 10 of the missing paths are foreign-repo files
- aspect: outline_vs_shipped: include_unrealised 8/19, of which 5 are D8 (#1605) and 3 are rename old-sides
- aspect: manifest_decisions: M6 outline_only 29, references_only 12
