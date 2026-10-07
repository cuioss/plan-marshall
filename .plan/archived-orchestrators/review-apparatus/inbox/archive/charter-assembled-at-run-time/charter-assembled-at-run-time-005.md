envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:19Z

component=project:finalize-step-plugin-doctor
category=bug
confidence=high

# Derive plugin-doctor scope from the realized diff, not affected_files

## Context

In plan `charter-assembled-at-run-time`, fix task TASK-17 was added mid-execute by operator ruling. It changed `tools-integration-ci`, `workflow-integration-github` and `workflow-integration-gitlab`, but never extended `references.affected_files`. The first `finalize-step-plugin-doctor` firing gated only 3 skill directories and warned that its scoped mode cannot see cross-skill divergence. The skills TASK-17 touched were missed until the orchestrator re-ran plugin-doctor on them by hand (the step's final record reads "6 skills gated"). The pre-submission self-review verifier later answered `may_close=no` because `github-impl.md` / `gitlab-impl.md` (siblings of that same surface) were unchecked.

## Root cause

The finalize step's scope read comes from `affected_files`, a declaration that does not grow when scope moves during execute. This is the downstream consequence of the secondary directive in lesson 2026-09-23-16-001.

## Proposed action

Compute the gated skill set from the realized branch diff (`manage-references compute-footprint` / `git diff base...HEAD`), unioned with `affected_files`. When the two disagree, log the extra skills as a scope-drift signal. Apply the same derivation to every finalize step that scopes by `affected_files`.

## Evidence

- aspect: request_result_alignment: 12 undeclared files from TASK-17
- aspect: logging_gap_analysis: scoped plugin-doctor warning over 3 skill dirs
- aspect: llm_to_script_opportunities: manual skill-dir selection by the orchestrator
- related lesson: 2026-09-23-16-001 (secondary directive)
