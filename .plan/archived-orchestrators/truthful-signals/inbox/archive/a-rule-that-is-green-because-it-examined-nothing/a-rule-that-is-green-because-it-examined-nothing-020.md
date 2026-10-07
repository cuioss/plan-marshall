envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:55:34Z

component=plan-marshall:manage-status
category=anti-pattern
title=Script-failure cluster 1/6 — manage-status invoked with a non-existent top-level subcommand
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:manage-status:manage-status

# Script-failure cluster 1/6 — manage-status invoked with a non-existent top-level subcommand

## Observation

```text
2026-08-08T12:46:07Z ERROR [ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:manage-status:manage-status
  exit_code=2 failure_kind=argparse_rejection
  detail=manage-status.py: error: argument command: invalid choice: …[truncated]
```

Fired during the phase-2-refine re-entry with baked-in clarifications. The invented verb itself is **not recoverable from the log** — the stored `detail` is truncated at exactly the point where the invalid choice is named, so the record proves *that* a verb-paraphrase happened without preserving *which* verb. That truncation is itself worth the epic's attention: an `argparse_rejection` record whose actionable payload is the rejected token should not be truncated before that token.

## Root cause class

Recurrence signature 1 from `agent-behavior-rules.md` § "Never invent script subcommands" — **verb-paraphrase**: synthesizing a verb that names the goal rather than quoting the declared subcommand. `manage-status` declares 26 top-level choices; the invoked one was outside the set.

## Why this cluster matters beyond the single call

This is **1 of 4 distinct notations in this single plan** that failed with an invented subcommand or flag (the others: `manage-findings`, `manage-solution-outline`, `manage-plan-documents` — see sibling candidate-lessons in this batch). The prohibition against inventing subcommands sits on the **always-loaded agent floor** (`persona-plan-marshall-agent` SKILL.md, plus the full recurrence-signature checklist in `agent-behavior-rules.md`), and it was violated four times in one plan anyway.

That is the finding. A rule that is loaded into every envelope and violated four times per plan is not being enforced by being written; the `ARGUMENT_NAMING_*` plugin-doctor cluster guards *authoring* drift in documentation, but nothing guards an agent's *runtime* invocation.

## Proposed action

- **Preserve the rejected token.** Stop truncating `argparse_rejection` detail before the invalid-choice value; the value is the entire diagnostic content of the record.
- **Consider a runtime assist rather than more prose.** The executor already knows the valid choice set at rejection time. Emitting the closest valid verb (edit distance over the `choices` list) into the failure TOON would convert a dead-end exit 2 into a self-correcting one, and would cost nothing on the success path.
- Measure before prescribing: four occurrences in one plan is a rate, and the epic should know whether it is typical before deciding the remedy's size.

## Evidence

- Work log entry `a35965`, 2026-08-08T12:46:07Z.
- Union-deduped by notation; this notation failed once in this run.
