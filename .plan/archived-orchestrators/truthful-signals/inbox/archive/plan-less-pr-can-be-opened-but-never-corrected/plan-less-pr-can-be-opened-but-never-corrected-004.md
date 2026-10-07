envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:05:33Z

component=plan-marshall:manage-run-config
category=anti-pattern
bundle=plan-marshall

# A hardcoded list that mirrors a dispatch table must be derived from that table

## Observation

`run_config.py` carried a hardcoded list of supported targets that duplicated the set already
declared by a dispatch table in the same surface. The two were correct at the moment of
writing and had no mechanism keeping them correct: adding a target to the dispatch table
leaves the mirror silently short, and nothing fails.

Found by CodeRabbit on PR #1065, remediated as TASK-016 by deriving the list from the
dispatch table.

The reviewer's phrasing is worth preserving verbatim as the rule: *per the project's own
path instructions, a hardcoded list mirroring a dispatch table's supported targets must
derive from that table.*

## Why this is the epic's theme

A mirrored list is a second source of truth that presents itself as a fact. Every consumer
that reads the mirror gets a confident answer about "the supported targets" — an answer that
is only as fresh as the last time a human remembered to sync it. The staleness is invisible
at the read site.

## Corrective rule

**When you find yourself typing a list whose members already exist in a table, a registry, a
dispatch map, or an enum elsewhere in the codebase, derive it instead of retyping it.**

- `sorted(DISPATCH.keys())` over a re-typed tuple.
- A module-level constant computed from the authority, not a literal placed beside it.
- If derivation is genuinely impossible (cross-module import cycle, ordering constraint), the
  mirror needs a test that asserts set-equality against the authority — the mirror is then
  guarded even though it is not derived.

## Relationship to existing archetypes

This is the same family as the standing "every set-guarding detector must be
population-derived" rule and the index-completeness obligation in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` ("a newly-authored
index/summary table must enumerate every member of the set it indexes"). All three are one
obligation seen from different angles: **a derived set must be derived, or guarded, but never
retyped.** The orchestrator may prefer to fold this into an existing lesson rather than file
it standalone.
