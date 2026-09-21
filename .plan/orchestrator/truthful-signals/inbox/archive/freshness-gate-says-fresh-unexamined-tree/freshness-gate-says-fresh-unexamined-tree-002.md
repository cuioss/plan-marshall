envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:08Z

component=plan-marshall:manage-status
category=bug
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Validate --head-at-completion as a real commit instead of trusting a typed SHA

## Context

`mark-step-done --head-at-completion` is declared in its own `--help` as
"Optional git SHA captured at step completion", persisted on the step record, and
"consulted by resumable phase dispatchers ... to decide whether to skip or re-fire
after the worktree HEAD has advanced". The argparse surface accepts any string.

Three times during this plan's finalize the orchestrator composed a full 40-character
SHA by expanding a short form it held rather than resolving it. Each was caught by a
reader and corrected. Verified after the fact: all four distinct persisted values
(`ca95c98`, `cac8556`, `3d40417`, `569ab66`) resolve to real commits, so the on-disk
record is clean.

## Root cause

The field's correctness depended entirely on attention. Nothing in the write path
tests whether the supplied value names a commit in the tree, and the value's only
consumer treats it as ground truth for a skip-or-re-fire decision.

A fabricated SHA fails toward re-firing rather than false-skipping, so the blast
radius is bounded — but `pre-push-quality-gate` fired 7 times and
`project:finalize-step-plugin-doctor` 5 times on this plan, and nothing distinguishes
a re-fire caused by a genuinely advanced HEAD from one caused by a value that never
matched anything.

## Proposed action

Resolve `--head-at-completion` through `git rev-parse --verify {value}^{commit}`
inside `_cmd_mark_step.py` and reject a value that names no commit in the tree.
The check is one subprocess call on a flag that is already optional, so nothing that
omits it changes; a caller that supplies a value gains a structural guarantee instead
of an attentional one.

Accepting the short form and storing the resolved full SHA would additionally remove
the expansion step that produced all three fabrications.

## Evidence

- aspect: llm_to_script_opportunities — 8 persisted `head_at_completion` values across 16 finalize steps, 3 fabrication attempts
- `manage-status mark-step-done --help` — the flag carries no validation and no `choices`
- `git cat-file -t` on all 4 distinct persisted values — all resolve to `commit`
- status.json — `pre-push-quality-gate.firing_count: 7`, `project:finalize-step-plugin-doctor.firing_count: 5`
