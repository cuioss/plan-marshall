envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:01:00Z

component=plan-marshall:manage-references
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Validate a footprint ledger by symmetric difference, never by cardinality

## Context

`references.affected_files` holds 29 entries. The merged footprint of PR #1342
(`git diff --name-only 77db1a0d3 91bbe7470`) holds 28.

| Measure | Value |
|---|---|
| cardinality delta | 1 file (3.4%) |
| symmetric difference | 13 files |
| union | 35 files |
| symmetric difference as share of union | **37.1%** |

A check that compares counts sees a 3.4% discrepancy and passes. The set is 37%
wrong. The near-match of the two counts is a coincidence that actively conceals the
divergence.

The 13 split cleanly by cause:

**Seven recorded but never changed** — every one is declared `intent: read` in the
outline:
`file_ops.py`, `manage-lessons.py`, `manage-metrics.py`, `error-handling.md`,
`billing-composition.md`, `run-config-standard.md`, `shim-marker-convention.md`.

**Six changed but never recorded** — execute-time additions:
`audit-archived-plan-retrospectives/SKILL.md`, `plugin-doctor/references/rule-catalog.md`,
and four test files.

## Root cause

Two distinct defects that happen to offset:

1. `affected_files` records read-intent and write-intent in one undifferentiated
   list. It is a **touch set**, not a footprint, and its name invites every
   consumer to read it as the latter. The outline itself distinguishes the two
   correctly, and `check-artifact-consistency` excludes read-intent correctly —
   only this ledger conflates them.
2. Files added during execute are not appended, so scope growth is invisible.

Because one defect over-reports by seven and the other under-reports by six, the
cardinality lands within 3.4% and any count-based validation passes.

## Proposed action

- Split the field, or add an `intent` discriminator, so a consumer asking "what did
  this plan change" cannot be answered with files it only read.
- Where a check validates this ledger against a realized footprint, compare the
  **sets** and report the symmetric difference, with each side's membership named.
  A cardinality comparison over two sets is not a check; it is a coincidence
  detector.

## Related

This composes with the previously recorded `affected_files`-vs-live-footprint
divergence finding, and supplies its mechanism: the divergence is not drift, it is
two systematic errors in opposite directions.

## Evidence

- `manage-references get --plan-id … --field affected_files` → 29 entries
- `git diff --name-only 77db1a0d3 91bbe7470` → 28 entries
- `manage-solution-outline list-deliverables` → the seven excess entries are exactly
  the `intent: read` declarations
