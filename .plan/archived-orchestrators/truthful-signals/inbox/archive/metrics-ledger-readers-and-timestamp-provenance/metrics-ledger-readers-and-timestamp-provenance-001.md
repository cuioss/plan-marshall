envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T19:59:54Z

component=plan-marshall:plan-marshall-plugin
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# A stale served skill body is indistinguishable from a live contract

## Context

This retrospective loaded `plan-marshall:manage-metrics` from plugin cache version
`0.1.1240`. The served SKILL.md documents the `record-dispatch-boundary`
`--termination-cause` enum as six values. The live argparse `choices` list accepts
twelve, and the repository's own `marketplace/bundles/.../manage-metrics/SKILL.md`
documents all twelve — with a contract test that discovers every occurrence in the
document and fails until each matches the `DISPATCH_TERMINATION_CAUSES` tuple.

The gap is not academic. Seventeen of this plan's own twenty-eight recorded
dispatch-boundary rows carry `step_complete` or `returned_with_findings`, neither of
which exists in the served body. Judged against the contract this agent was handed,
61% of the plan's own ledger reads as invalid.

The same session had already hit this: the operator was asked mid-run to repair a
`dist-manifest.json` that regressed from `0.1.1527` to `0.1.1240`, after
`phase-6-finalize` loaded a body missing `emit-landing.md` and six other files.

## Root cause

A loaded skill body carries no version, no freshness claim, and no way for the
consuming agent to tell a current contract from a stale one — while the agent's
governing rules instruct it to obey the loaded body. The failure is silent in both
directions: an agent may reject valid data as contract-violating, or file a
doc-drift defect against a document that is already correct.

## Proposed action

Make the served body self-identifying, so that a consumer can detect staleness
without a second source:

- Stamp the served bundle version into the loaded body (or expose it through a
  cheap verb an agent can call), so an agent can compare what it was served
  against what the executor resolves.
- Where a skill body enumerates a vocabulary that a script's argparse also
  enumerates, prefer directing the reader to `--help` over restating the set — a
  restatement is exactly what goes stale invisibly.

Note this is NOT a request to re-litigate the plugin-cache pin repair, which is
operator-owned. It is about the consumer's inability to notice.

## Evidence

- served body (cache 0.1.1240): six-value enum
- `manage-metrics record-dispatch-boundary --help`: twelve-value enum
- repository SKILL.md lines 423-444: twelve values plus a stated contract test
- aspect log_analysis: 17 of 28 boundary rows carry `step_complete` /
  `returned_with_findings`
- aspect chat_history_analysis: operator escalation to repair the regressed pin

## How this retrospective avoided acting on it

The workflow body was read from repository source rather than from the cache, and
the enum discrepancy was cross-checked against `--help` and the repo document
before anything was filed. Had it been taken on trust, this report would have
carried a false doc-drift finding against a correct document.
