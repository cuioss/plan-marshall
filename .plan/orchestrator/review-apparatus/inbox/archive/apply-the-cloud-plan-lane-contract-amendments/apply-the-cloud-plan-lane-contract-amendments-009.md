envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:28:06Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
created=2026-09-05

# A registered-verb rejection is a doc-read that never happened, not a typo

## Observation

Plan `apply-the-cloud-plan-lane-contract-amendments` produced **18 argparse rejections
(exit 2, `failure_kind=argparse_rejection`) across 9 distinct script notations** in one run.
Seven of the eighteen, spanning five notations, were *verb*-shaped: the caller named a
subcommand the script does not register.

| Time (UTC) | Notation | Rejected shape |
|---|---|---|
| 12:19:03 | `plan-marshall:manage-config:manage-config` | `finalize-steps` — registered: `apply-preset`, `list-ask-lane`, `set-lane` |
| 12:32:23 | `plan-marshall:manage-config:manage-config` | a sub-verb under `plan` — registered: `phase-1-init` … `phase-6-finalize` |
| 12:39:10 | `plan-marshall:manage-solution-outline:manage-solution-outline` | resolved to `get-deliverable` |
| 13:48:37 | `plan-marshall:tools-integration-ci:ci` | a verb under `checks` — registered: `logs`, `pull-request-runs`, `rerun`, `status`, `wait`, `wait-for-status-flip` |
| 02:19:55 | `plan-marshall:manage-status:manage-status` | resolved to `assert-step-recorded` |
| 06:10:43 | `plan-marshall:manage-solution-outline:manage-solution-outline` | resolved to `list-deliverables` |
| 06:22:07 | `plan-marshall:manage-metrics:manage-metrics` | a top-level verb — registered: `accumulate-agent-usage` … `start-phase` |

## Why this is one shape, not five defects

Every one of the five notations publishes a `## Canonical invocations` block naming its exact
verb set, and the executor's rejection message *prints that same set back*. So the loss is never
a missing affordance — it is that the verb was extrapolated from surrounding workflow prose or
from a sibling script's surface **before** the canonical block was read. Two of the seven
(`get-deliverable`, `list-deliverables`) are on the *same* script at opposite ends of the run,
which rules out "the doc is hard to find" and leaves "the doc was not consulted".

The existing rule (`persona-plan-marshall-agent` § "Never invent script subcommands") already
prohibits this and enumerates five recurrence signatures. This run is evidence the prohibition
is not converting into behaviour at the point of the call.

## Proposed corrective action

The rule is stated where a caller reads it once at load time, but the call happens hundreds of
turns later. Consider moving the enforcement to where the guess is made rather than where the
principle is stated — e.g. a per-notation verb set surfaced at dispatch time to the workflows
that call a given script, so the accept-set is resident in the same context as the call.

## Scope note

This is the *verb* half of the run's argparse loss. The *flag* half (11 rejections, 6 notations)
is a separate candidate with a different cause, and the band in which both concentrate is a
third. They are filed separately rather than as one "18 argparse rejections" message because
the remedies do not coincide.
