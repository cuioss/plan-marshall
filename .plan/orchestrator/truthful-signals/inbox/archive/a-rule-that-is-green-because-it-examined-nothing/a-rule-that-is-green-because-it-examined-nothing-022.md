envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:56:28Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
title=Script-failure cluster 3/6 — `--deliverable N` invented where the verb declares no such flag
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:manage-solution-outline:manage-solution-outline

# Script-failure cluster 3/6 — `--deliverable N` invented where the verb declares no such flag

## Observation

```text
2026-08-08T13:23:16Z ERROR [ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:manage-solution-outline:manage-solution-outline
  exit_code=2 failure_kind=argparse_rejection
  detail=manage-solution-outline.py: error: unrecognized arguments: --deliverable 1
```

Fired early in phase-4-plan, while reading deliverables to author tasks.

## Root cause class

A **flag** paraphrase rather than a verb paraphrase — the fifth shape, not covered by the four documented recurrence signatures, which all concern subcommands or the `--plan-id` / `--phase` / `--resolution` flag family.

`manage-solution-outline` declares `get-deliverable` as a dedicated verb; the invocation instead reached for a general read plus a `--deliverable` selector. The invented flag is a reasonable *design* for the CLI — it is simply not the design that exists.

## Why this one is distinct from clusters 1, 2 and 4

Clusters 1/2/4 are verb paraphrases against an argparse `choices` set, where the rejection message enumerates the valid alternatives. This one is `unrecognized arguments`, which enumerates **nothing** — the caller learns the flag is wrong and gets no hint what the right selector is.

That asymmetry matters for any mechanical remedy: a "nearest valid verb" assist works for `invalid choice` and does nothing for `unrecognized arguments`. Closing the flag case needs the parser's declared option strings for the resolved subcommand, which argparse also has but does not print.

## Proposed action

- Extend any executor-side failure assist to cover **both** argparse rejection shapes: `invalid choice` (suggest nearest verb from `choices`) and `unrecognized arguments` (suggest nearest declared option string for the resolved subparser).
- Add flag-paraphrase as an explicit fifth recurrence signature only if the mechanical remedy is rejected — see the argument in cluster 2/6 for why another documented signature is unlikely to change the rate on its own.

## Evidence

- Work log entry `c7624c`, 2026-08-08T13:23:16Z.
- Canonical alternative: `manage-solution-outline get-deliverable` (declared in the verb set printed by the rejection itself).
