envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:00:16Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Record a step's partial failure in structured facts, not only in display_detail

## Context

`branch-cleanup` recorded:

```
outcome: done
facts: { action: merged, upstream_commit_count: 0, merge_mechanism: merge_queue,
         merge_state: merged, work_performed: true }
display_detail: "merged #1342 via queue, main pulled, worktree removal timed out"
```

Every structured field asserts unqualified success. The timeout exists only inside
the human-readable prose string. A machine reader of `status.metadata.phase_steps`
sees a clean `done`.

The residue was not inert. The worktree was left half-torn-down on disk, and
`git status --porcelain` inside it reports four deleted root files: `LICENSE.md`,
`build.py`, `pw`, `pw.bat`.

`check-artifact-consistency`'s footprint resolver prefers a live worktree diff
(`{base}...HEAD` union porcelain) whenever a worktree is on disk. It found the
torn-down one, absorbed those four deletions, and produced a footprint containing
four files that belong to no part of this plan — all four were last modified
upstream in PRs #1074-#1230. The check then reported `pass`.

## Root cause

Two independent decisions compose badly. First, a step's outcome vocabulary has no
representation for *partially* completed, so a step that did its primary job and
failed its cleanup records `done`. Second, a downstream consumer treats
"a worktree exists on disk" as evidence that the worktree is a valid picture of the
plan — a premise the interrupted teardown falsifies.

## Proposed action

1. Add a structured residue field to the step record (for example
   `facts.worktree_removal: timed_out`) so a partial completion is machine-visible.
   The rule generalises: any outcome a human reads in `display_detail` and a tool
   cannot read in `facts` is a signal that exists only by accident.
2. Have the footprint resolver reject a worktree whose teardown was recorded as
   incomplete, and fall through to the persisted realized-footprint capture, rather
   than trusting mere presence on disk.

## Evidence

- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]`
- `git -C .plan/local/worktrees/metrics-ledger-readers-and-timestamp-provenance status --porcelain` → four ` D` rows
- aspect artifact_consistency: `references_only` contains LICENSE.md, build.py, pw, pw.bat
- `git log 77db1a0d3 -- pw pw.bat LICENSE.md build.py` → last touched in #1230/#1174/#1074
- the merged footprint (`git diff --name-only 77db1a0d3 91bbe7470`) contains none of the four
