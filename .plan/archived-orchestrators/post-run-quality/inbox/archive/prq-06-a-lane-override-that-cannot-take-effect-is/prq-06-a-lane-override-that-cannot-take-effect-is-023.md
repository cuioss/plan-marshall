envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:48:51Z

component=plan-marshall:tools-script-executor
category=anti-pattern

# Ten argparse rejections across eight scripts, and the one that mattered most had its own answer printed in the error

Signal 3 for this plan is 15 distinct failing notations over 26 total failures. Two clusters are reported separately (the 8 `architecture search` invented-flag rejections, and the 4 notation underscore/hyphen internal errors). This message covers the remaining cluster: **plain argparse rejections, `exit_code: 2`, spread thin across eight different scripts** — no single one frequent enough to notice, ten of them in aggregate.

## The population

| notation | verb | occurrences |
|---|---|---|
| `plan-marshall:manage-findings:manage-findings` | `qgate` | 3 |
| `plan-marshall:manage-references:manage-references` | `set-list` | 2 |
| `plan-marshall:manage-status:manage-status` | `phase_handshake` | 1 |
| `plan-marshall:manage-tasks:manage-tasks` | `add` | 1 |
| `plan-marshall:manage-execution-manifest:manage-execution-manifest` | `read` | 1 |
| `plan-marshall:phase-6-finalize:ci_complete_precondition` | `resolve` | 1 |
| `plan-marshall:phase-6-finalize:ci_verify` | `run` | 1 |
| `plan-marshall:tools-integration-ci:ci` | `pr` | 1 |

## The instructive instance

The `ci pr` rejection is the flag-POSITION class, not the flag-existence class:

> `ci.py: error: unrecognized arguments: --plan-id prq-06-…` — **"note: `--plan-id` is a top-level flag and belongs BEFORE the verb"**

The script already diagnoses the mistake and states the fix, in the rejection itself. The caller had the answer the moment it failed. This is the router-scoped-flag signature the `execution-context` contract documents at length — `--plan-id` is consumed by the `ci` router ahead of the first verb token for read verbs, and declared AFTER the verb on the body-consumer subcommands — and it is precisely the case where "consult the canonical-invocation block" is cheaper than one round-trip through argparse.

## Rule

Two separable asks:

1. **For callers** — a flag's POSITION is part of its declaration, not a detail. Read the script's canonical-invocation block rather than transposing a flag that worked on a sibling verb. The five recurrence signatures are already enumerated in `agent-behavior-rejection` guidance; the `ci` router case is the one this plan hit.
2. **For the executor** — when a rejection carries a corrective note this precise, the note is a candidate for structured emission rather than free-text stderr. Ten `exit_code: 2` failures that each already knew their own remedy is a signal the remedy is not reaching the caller in a usable shape.

## Scope note

The three clusters together (8 + 4 + 10 = 22 of 26 total failures) account for nearly all of this plan's script-failure surface, and none of them is a product defect — all three are call-construction drift against declarations the scripts publish.
