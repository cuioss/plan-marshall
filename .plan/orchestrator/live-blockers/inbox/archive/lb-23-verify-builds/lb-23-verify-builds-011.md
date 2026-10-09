envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:02:00Z

component=plan-marshall:manage-references
category=bug
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Keep references.affected_files current with the branch diff during finalize

## Context

On plan lb-23-verify-builds `references.affected_files` held 46 entries while the branch touched 56 files. The scoped plugin-doctor gate derives its skill directories from that field, so its first two firings gated 10 skill directories while the branch touched 14. The four ungated directories were `manage-change-ledger`, `execute-task`, `plan-marshall` and `ref-workflow-architecture`. From the third firing on the leaf gated the union of the field and the branch diff by hand, because the orchestrator asked it to check.

## Root cause

The field is the declared surface synced from the outline; files changed by fix tasks, by self-review fix commits and by test side effects never enter it. Finalize steps that read it as "what the plan changed" are reading a declaration, not the realized footprint. The retired `modified_files` field has the same consumer problem: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` Step 1 still calls `manage-references get --field modified_files`, which returned `field_retired` on all 8 firings (existing lesson 2026-10-08-21-001).

## Proposed action

- Have every finalize step that needs "what changed" call `manage-references compute-footprint` (which returned 52, then 55, then 56 files as the branch grew), never `affected_files`.
- Fix the housekeeping step document to the same call.
- Keep `affected_files` as the declaration it is, and name it so in the plugin-doctor step document.

## Evidence

- aspect: artifact_consistency - `affected_files_exact_match: warn`, 10 realized-but-undeclared paths, forwarded to the manifest aspect.
- aspect: manifest_decisions - `declared_vs_realized_set: fail`, 0 declared-but-unrealized, 10 realized-but-undeclared; diff 56 files (17 production, 23 test, 16 documentation).
- aspect: outline_vs_shipped - 14 of 56 footprint paths carry no outline assessment.
- aspect: chat_history_analysis - plugin-doctor: "references.affected_files (46 entries) yields only 10 skill directories. The branch diff against origin/main touches 14"; work log: "manage-references get --field modified_files is retired".
