envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:34Z

component=plan-marshall:phase-6-finalize
category=improvement
title=phase-6-finalize merge gate: bot summary comments reopen findings on every edit and the merge step's own PR note becomes a finding
source_lesson=2026-11-22-21-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# phase-6-finalize merge gate: bot summary comments reopen findings on every edit and the merge step's own PR note becomes a finding

- Source signal: finalize merge gate of plan-12-forms-kinds-schema-layout (PR 54), gate result `blocking_findings_present`.

## What happened

The findings-store gate (`blocking_findings_present`) is checked before the participation check. Three things made it block repeatedly:

- A review bot edits its summary comment on every run. Each edit reopened the finding that had been resolved for the earlier version of the comment.
- A PR note posted by the merge step itself was fetched by the next review-comment read and became a finding, so the gate blocked on text the plan had written.
- The findings gate is checked before the participation check, so the participation block only became visible once the findings block was cleared.

## Why it matters

Each reopen costs a triage round with no code change behind it, and the loop looks like the review failing to converge when the code is already clean.

## Candidate rule

- Match a bot summary comment by the comment id and the author, and keep a resolution across edits when the diff of the comment body adds no new finding text.
- Mark comments written by the plan's own steps (merge note, status note) with a marker, and let the fetch skip them.
- Evaluate the participation check and the findings check together and report both, so one run shows the whole block.
