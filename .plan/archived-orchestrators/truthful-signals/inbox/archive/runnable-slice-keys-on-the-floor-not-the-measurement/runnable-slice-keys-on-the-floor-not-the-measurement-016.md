envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:12:00Z

component=plan-retrospective
category=bug
created=2026-07-29

# Retrospective measures a footprint after branch-cleanup deletes the worktree

`check-artifact-consistency` reported
`affected_files_recall — fail — Recall 0% below 70% threshold`, listing all 20
declared files as missing. The true footprint is 21 files (verified against merge
commit `57e1daec3`) and true recall is 17/20 = 85% — comfortably above the 70%
threshold. The check is a FALSE FAILURE.

The cause is manifest step ordering. The aspect derives the footprint live from
the plan's worktree; `branch-cleanup` removed that worktree at 05:58:15Z; the
manifest orders `plan-marshall:plan-retrospective` AFTER `branch-cleanup`. So the
footprint source was gone before the measurement ran, and an absent source was
reported as a measured zero.

This is the same finalize-ordering archetype as the known PLAN-10 defect (a plan
that fixes a finalize-time component cannot have that fix exercised by its own
finalize) — but with a sharper edge: it produces a confident numeric verdict
rather than a skip. "Recall 0%" reads as a catastrophic planning failure. The
honest output is "footprint source unavailable — not measured".

The three genuinely-undeclared files (`build-systems-common.md`,
`manage-execution-manifest/SKILL.md`, `phase-5-execute/SKILL.md`,
`ref-workflow-architecture/standards/agents.md`) and the three declared-but-
read-only files are the real, small signal this check exists to surface, and the
false 0% buries it.

## Impact

Two fixes, either sufficient. (1) Order `plan-marshall:plan-retrospective` BEFORE
`branch-cleanup` in the finalize manifest, so the worktree it measures against
still exists. (2) Make the aspect fall back to the merge/branch commit range when
the worktree is absent, and — regardless — emit `status: skipped` with an
`unavailable_footprint_source` reason rather than a 0% recall failure when it has
nothing to read. A measurement with no input must report "not measured", never
"measured zero".

Separately: the `Affected files` declaration mixes write-intent and read-intent
targets (TASK-001 steps 11-15 carry `intent: read`), so recall computed over that
flat list structurally cannot reach 100% for any plan declaring reconciliation
reads.
