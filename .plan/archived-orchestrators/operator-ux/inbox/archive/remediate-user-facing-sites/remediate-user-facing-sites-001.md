envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:40:05Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=remediate-user-facing-sites

# Resolve the self-review base ref against the remote before surfacing files

## Context

The `pre-submission-self-review` step's file surfacer defaulted to a stale local base ref and
surfaced 108 files as the review surface. The plan's realized footprint was 26 files, all of
them recorded in `references.json` and confirmed at 100% recall by the artifact-consistency
aspect. The 82-file difference was base-authored work the plan never touched.

The dispatch noticed the discrepancy itself and re-scoped to `origin/main`, so the review that
ran was correctly scoped. But nothing in the workflow validates the base ref before the surface
is computed, so the correction depended entirely on the agent spotting a file count that looked
wrong. The step fired 7 times on this plan; a quieter instance of the same defect would have had
the reviewer read 4x the intended surface without anyone noticing.

## Root cause

The surfacer takes whatever base ref the local checkout resolves to rather than resolving the
recorded `references.json` `base_branch` against the remote. A worktree whose local `main` is
behind `origin/main` therefore yields a diff that includes every upstream commit the worktree has
not seen.

## Proposed action

Resolve the base ref inside the file surfacer against `origin/{references.base_branch}` rather
than against a local ref, and add a sanity refusal: when the surfaced file count exceeds the
plan's recorded footprint by more than a stated factor, refuse with a named error instead of
returning the oversized surface. Both halves are deterministic and belong in the script, not in
agent judgement.

## Evidence

- aspect: plan_efficiency — `pre-submission-self-review` recorded `firing_count: 7` with three
  `loop_back` outcomes; the step sits on the finalize loop that consumed 59% of plan tokens.
- aspect: artifact_consistency — `affected_files_recall: 100%`, `declared: 26`, `found: 26`,
  `outline_only[0]`, `references_only[0]`. The 26-file footprint is unambiguous, so the 108-file
  surface cannot be explained by an under-recorded footprint.
- aspect: llm_to_script_opportunities — logged as candidate 1, complexity low, repetition 7.
