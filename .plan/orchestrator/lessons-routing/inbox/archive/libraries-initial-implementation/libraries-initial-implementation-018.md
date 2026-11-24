envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:11Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: self-check criteria against Affected files and forward references before the Q-Gate
source_lesson=2026-11-18-18-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase-3-outline: self-check criteria against Affected files and forward references before the Q-Gate

# Candidate lesson: outline consistency defects reach the Q-Gate instead of being caught while the outline is written

- Source signal: plan git-worktrees-import (inbox plan-03-git-worktrees-import-001 and -002), two phase-3-outline Q-Gate findings, both resolved `taken_into_account`.

## What happened

1. `scope_criterion_validator` (finding 86382b, under-coverage): a deliverable's success criterion required a statement in `doc/specification/git-worktrees.adoc`, a file that was not in that deliverable's Affected files. The file belongs to a later deliverable that already carried the same criterion, so the earlier deliverable could not meet its own criterion at completion. The run left the outline unchanged and scoped the tasks to the Affected files.
2. `request_alignment` (finding f95cde): the request asked for a plain copy of existing code. One deliverable's note departed from the source (an atomic directory claim) and said "see the open question below", but the outline had no open-question section, so the departure was declared and never put to the owner. The owner decision was obtained later through a question, and the outline was not corrected.

## Root cause

The outline author does not check its own text for two mechanical inconsistencies: a criterion that names a file outside its deliverable's Affected files, and a forward reference to a section that does not exist. Both are found only by the Q-Gate after the outline is complete.

## Candidate rule

- Add an outline self-check before the Q-Gate: every file named by a deliverable's success criterion must be in that deliverable's Affected files (or the criterion moves to the deliverable that writes it).
- Flag a reference such as "see the open question below" when the outline has no such section. For a take-over or plain-copy request, require an explicit open question or recorded owner decision for every departure from the source.


## Recurrence in the next plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-001)

- Source signal: Q-Gate finding 619fec (phase 3-outline, warning, resolved `taken_into_account`).
- Deliverable 2 added `REFUSED_BY_POLICY` to the `worktreeStatus` Javadoc unconditionally ("settled by deliverable 5"), while deliverable 6 added the same outcome to the specification only "if deliverable 5 shows StatusCommand runs a clean filter". Had the hypothesis been refuted, Javadoc and specification would have disagreed. The task wording resolved it (the entry written unconditionally as the interface-level guarantee).

Same family as above (an outline consistency defect that reaches the Q-Gate), with one sharper rule: when an outline contains an investigation deliverable whose result is still open, every other deliverable documenting the same contract must either depend on that result in the same way or state the independent reason why the statement holds regardless. An earlier deliverable must not assert what a later one is still to settle.


## Recurrence in a later plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-002)

- Source signal: phase-3-outline Q-Gate `scope_criterion_validator`, finding e18e3f (under_coverage, severity warning, file `README.adoc`), resolved `taken_into_account`.
- Deliverable 4's criterion read "the AsciiDoc link check over `doc/` and over `README.adoc` reports nothing unresolved", but its verification command ran only `asciidoc verify-links --directory doc --recursive`, so the root `README.adoc`, outside `doc/`, was never checked. The fix was a second call, `asciidoc verify-links --file README.adoc`.

Same family as above (a criterion and the deliverable's own checkable scope disagree, found only by the Q-Gate). Sharper rule: a criterion that names more than one scope (a directory plus a root-level file) gets one verification call per scope, or is narrowed to what the command checks; a root-level file named beside a directory gets its own file-scoped check. Add it to the outline self-check proposed above. Related: lesson 2026-11-20-14-001 (verification commands drawn from the canonical list).
