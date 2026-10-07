envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:05Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
rank=1
source_plan=truth-166-architecture-refresh-migration-churn

# Give plan_creation_sha a writer or retire the scope-creep guard it gates

## Context

`scope_creep_check` is the pre-task scope-creep guard for `phase-5-execute`. It reads
`plan_creation_sha` from `references.json` to obtain the baseline it diffs the worktree
against. That field has no producer anywhere in the tree: a content sweep over 2911
inventoried files with clean coverage (no unreadable files, no truncation, no elided
buckets) found the literal `plan_creation_sha` in only the consumer script (4 matches),
the consumer's own `phase-5-execute/SKILL.md` (2), and three test files. No writer.

This plan's `references.json` carries `branch`, `base_branch`, `scope_estimate`,
`domains`, `track`, `affected_files`, `read_intent_files`, `domains_provenance` and
`pr_number` — and no `plan_creation_sha`. The guard therefore returned
`could_not_look` / `no_baseline_sha` on every one of the plan's 16 tasks, as it must on
every task of every plan.

## Root cause

The honesty half of the guard was built and the producer half never was. The
`_emit_could_not_look` path is meticulous — a dedicated docstring section explains that
`residual_count` is OMITTED rather than reported as `0` precisely so "an UNMEASURED run
cannot render as a measured clean one" — but the branch that reaches it is unconditional,
because the field it tests for is never written.

## Proposed action

Either write `plan_creation_sha` at plan creation (the natural producer is
`manage-references` at init, stamping the main SHA the plan was created against), or
retire the guard and its threshold config rather than shipping a check that cannot fire.

Prefer the writer: the guard's logic is correct and its residual/threshold model is sound.

## Evidence

- aspect: script_failure_analysis / logging_gap_analysis — the guard contributed zero
  coverage on a plan whose realized footprint grew to 26 paths against 22 declared.
- source: `phase-5-execute/scripts/scope_creep_check.py:212` — `base_sha =
  refs.get('plan_creation_sha')`, then `if not base_sha: return _emit_could_not_look(...)`.
- source: `architecture search --content --literal --pattern plan_creation_sha` —
  10 matches in 5 files, all consumer, consumer-doc or test; `files_scanned: 2911`,
  `unreadable[0]`, `truncated: false`, `elided[0]`.

## Generalizes

A could-not-look state that fires on **every** invocation is an INERT guard, not an
honest one — and the honesty machinery around it reads as diligence while buying zero
coverage. The detector is cheap and mechanical: for every field a guard reads as its
baseline, assert that some producer writes it. A reader-only field is the signature, and
one content sweep answers it.
