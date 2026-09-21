envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:07:57Z

component=plan-marshall:tools-permission-doctor
category=anti-pattern
title=Project allow-list grants 3 of 6 project finalize-step skills, so the operator is prompted for the rest

# Project allow-list grants 3 of 6 project finalize-step skills, so the operator is prompted for the rest

## Context

During plan `a-refusal-is-recorded-as-a-refusal-the-record` the operator interrupted the run:

> "Stop here: Why do you need to always ask for permission on stuff you are allowed to. Analyze carefully"

That is an operator-observed workflow break, not an inference, and the retrospective's permission aspect grades it `error` under the severity floor (the operator did not merely tolerate the prompt — they stopped the run over it).

The configuration explains it. `.claude/settings.local.json` `permissions.allow` carries these `Skill(...)` entries:

- `Skill(finalize-step-deploy-target)` + `Skill(finalize-step-deploy-target:*)`
- `Skill(finalize-step-plugin-doctor)` + `Skill(finalize-step-plugin-doctor:*)`
- `Skill(finalize-step-pre-submission-self-review)` + `Skill(finalize-step-pre-submission-self-review:*)`
- `Skill(finalize-step-sync-plugin-cache)`

Six project finalize-step skills are registered. Three are **absent** from that list, and all three ran in this plan:

- `finalize-step-lessons-housekeeping` — `firing_count: 5`
- `finalize-step-era-stamp-fill` — completed
- `finalize-step-review-retrospective` — completed

Two further defects sit in the same list: `Skill(finalize-step-pre-submission-self-review)` matches **no registered component** (the live step id is the plan-marshall built-in `pre-submission-self-review`), and `Skill(finalize-step-sync-plugin-cache)` carries only the bare form while its three siblings carry both the bare and `:*` forms.

Separately, `permissions.allow` contains **no `git` pattern of any kind**, while granting `Bash(python3:*)` and `Bash(python3 *)` — the same permission twice.

## Root cause

The allow-list is hand-curated one skill at a time, as each new prompt is encountered, so it records the history of which prompts happened to annoy someone rather than the set of components the workflow actually invokes. It has no derivation from the component registry, so it drifts in both directions at once: entries that match nothing survive, and registered components that run on every plan are missing.

## Proposed action

1. Add the three missing entries (both bare and `:*` forms), and normalise `finalize-step-sync-plugin-cache` to carry both.
2. Remove or correct the `finalize-step-pre-submission-self-review` entry, which matches no component.
3. Add a narrow git read allowance (`Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`) rather than leaving every direct git call to prompt.
4. The generalizable fix: derive the project finalize-step allow entries from the registered component set instead of accreting them, and add a check that reports allow entries matching no registered component — a hand-curated permission list is a set-guarding surface and should be population-derived like any other.

## Evidence

- aspect: chat_history_analysis — operator turn 8, verbatim; the run was interrupted, not merely nagged
- aspect: permission_prompt_analysis — 4 prompt rows, 3 `missing_permission` on project skills plus 1 on git
- config: `.claude/settings.local.json` `permissions.allow`
- artifact: `status.json` `metadata.phase_steps["6-finalize"]` — all three unpermitted skills recorded as run, `lessons-housekeeping` with `firing_count: 5`
