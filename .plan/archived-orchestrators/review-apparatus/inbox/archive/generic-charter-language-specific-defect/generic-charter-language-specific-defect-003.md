envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T16:49:53Z

# The dispatch audit's envelope allowlist has drifted behind the agent roster it guards

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_aspects: execution_context_dispatch_audit, logging_gap_analysis

## Context

`standards/execution-context-dispatch-audit.md` defines `envelope_violation` by an enumerated allowlist: any `[DISPATCH]` line whose `target=` falls outside `{execution-context, execution-context-level-1 … execution-context-level-7}` is a hard-rule finding.

This plan dispatched `target=execution-context-reader-level-5` to unblock TASK-9's upstream source citations (work.log 2026-08-09T11:18:40Z). That target is **not** in the allowlist — yet it is canonical. `platform-runtime/standards/pretooluse-enforcement.md` names the family verbatim while describing the enforcement hook's context gate: "the identity value is bundle-qualified — e.g. `plan-marshall:execution-context-level-4` (and `plan-marshall:execution-context-reader-level-N` for readers)". The agent file `marketplace/bundles/plan-marshall/agents/execution-context-reader.md` exists, and the reader/orchestrator/writer isolation the `untrusted-ingestion` contract mandates is exactly why this dispatch used it.

So a literally-applied audit flags a **compliant** reader dispatch as a hard-rule violation. Worse than a false positive: the finding shape carries `severity: error` with no warning tier, and the remediation guidance tells a maintainer the caller "routed it through the wrong target — typically a copy-paste mistake", which points the fix at the correct call site instead of at the stale rule.

The same aspect has a second population defect in the same run. `DISPATCH_TERMINATION_CAUSE` reads only `work/metrics-dispatch-boundaries-5-execute.toon`. This plan's finalize phase recorded **7** dispatch rows against execute's 4, and the plan's only `termination_cause=error` row (pre-submission-self-review, 293,089 tokens) sits in the finalize file. The larger population, containing the only failure, is outside every rule in the aspect.

## Root cause

Both are the same shape: a retrospective rule-set hard-codes a population by enumeration, the population grows, and nothing fails until an audit silently mis-grades. The allowlist and the phase scope are each written as a literal set in prose, with no derivation from the roster or the artifact set they are meant to cover.

## Proposed action

1. Derive the `envelope_violation` allowlist from the agent roster (the `execution-context*` agent files actually present in the bundle) rather than from a prose enumeration, and cover the derivation with a set-equality test in both directions — the pattern `test_plan_efficiency_anchors.py` already uses for the anchors table's two axes.
2. Widen `DISPATCH_TERMINATION_CAUSE` to every `work/metrics-dispatch-boundaries-*.toon` present, not `5-execute` alone; report the distribution per phase so a finalize-side `error` row is visible.
3. This is the second recorded instance of the archetype in the retrospective's own rule-sets. Retained lesson `2026-08-08-20-001` records "four plan-retrospective cross-checks hard-code a drifted population" — this adds two more sites in a file that lesson does not cover, which argues for a structural sweep rather than another point fix.

## Evidence

- aspect: execution_context_dispatch_audit — `ruleset_population_drift` finding; 17 of 17 dispatch lines enumerated, one carries `execution-context-reader-level-5`
- `standards/execution-context-dispatch-audit.md:51` — the enumerated allowlist
- `platform-runtime/standards/pretooluse-enforcement.md:37-38` — `execution-context-reader-level-N` named as canonical
- `marketplace/bundles/plan-marshall/agents/execution-context-reader.md` — the agent exists
- aspect: logging_gap_analysis — 6-finalize carries 7 dispatch rows including the only `termination_cause=error`; the rule reads the 5-execute file only
- retained lesson `2026-08-08-20-001` — same archetype, four other sites
