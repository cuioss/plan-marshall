envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:56:04Z

component=plan-marshall:manage-findings
category=anti-pattern
title=Script-failure cluster 2/6 — `qgate query` invented for the canonical `qgate list`
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:manage-findings:manage-findings

# Script-failure cluster 2/6 — `qgate query` invented for the canonical `qgate list`

## Observation

```text
2026-08-08T13:16:34Z ERROR [ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:manage-findings:manage-findings
  exit_code=2 failure_kind=argparse_rejection
  detail=manage-findings.py qgate: error: argument action: invalid choice: 'query'
         (choose from 'add', 'list', 'resolve', 'clear')
```

Fired between the 3-outline Q-Gate pass and the outline revision.

## Root cause class

Recurrence signature 1 — **verb-paraphrase**. `qgate query` reads naturally in workflow prose describing "querying the Q-Gate findings", but the declared action set is `{add, list, resolve, clear}`.

This exact invented-vs-canonical pair (`qgate query` → `qgate list`) is **already named verbatim** in `agent-behavior-rules.md` § "Never invent script subcommands — recurrence signatures", signature 1, as a concrete example from the lesson catalogue.

## Why this instance is the sharper data point

The documented remedy for this failure class is a checklist of four recurrence signatures, and **this call reproduced the first worked example in that checklist**. The checklist is loaded into every envelope by `persona-plan-marshall-agent`.

An enumerated example that is loaded into context and then reproduced verbatim is evidence that **the countermeasure class is wrong**, not that the checklist needs another entry. Adding a fifth signature to a list whose first entry was just re-violated has no mechanism by which it would work.

## Proposed action

Prefer a mechanical remedy over an additional documented signature:

- **Fail-with-suggestion at the executor boundary.** `execute-script.py` can catch the argparse `SystemExit(2)`, extract the `choices` tuple already present in the error text, and return a TOON carrying `nearest_valid_verb`. The information is present at the failure site; it is simply discarded.
- **Or fail-forward on an unambiguous single-nearest match** behind an explicit opt-in, so the common paraphrase costs a warning rather than a dead call.
- Either way, the argument for *more prose* is empirically weak here: the prose existed, was loaded, and named this exact call.

## Evidence

- Work log entry `aec23c`, 2026-08-08T13:16:34Z.
- Companion clusters in this batch: `manage-status`, `manage-solution-outline`, `manage-plan-documents` — four distinct notations, same archetype, one plan.
