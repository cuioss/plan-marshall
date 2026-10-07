envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:12:29Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Convergent remedy for an over-claiming sentence is deletion, not correction

## Context

`pre-submission-self-review` fired eight times on this plan: seven `failed`, one `done`.
It raised nine findings, eight classed `contract_drift` and one
`same_document_contradiction` — in every case a sentence stating a count, a condition or
an enumeration that the code no longer implements.

Four of the nine independently reached the same remedy, and each said so in its own
finding text:

- `cdda73` — "Convergent remedy is DELETION of the trailing clause, not correction"
- `44a042` — "Convergent remedy is DELETION of the parenthetical at 900, not a re-sync
  to 'two'"
- `24510f` — "Convergent fix: DELETE the over-claiming parenthetical (the sub-doc owns
  the condition)"
- `692ad6` — "Remedy: DELETE the comment rather than re-word it"

One round supplies the proof. Finding `cdda73` is marked SELF-SEEDED: it is a defect in
prose that the *previous round's own fix* (commit `926c39548`) had just authored. That
fix corrected a count; the corrected count was itself a second, independently driftable
derivation of a sweep the paragraph cannot see; the next round found it false in the very
tree that shipped it.

## Root cause

A restated fact is a copy. Correcting a copy leaves a copy — the same drift surface, now
with a fresh timestamp and the appearance of having been checked. Deleting it removes the
surface, provided a single source of truth already states the fact. In all four cases one
did, and each finding named it.

The self-review loop is what makes this measurable. Because the loop re-reads its own
output, a correction that re-seeds surfaces as a NEW ROUND rather than as a latent defect
nobody ever sees. Ordinary review has no such feedback path, which is why the pattern is
invisible outside a loop.

## Proposed action

State this as a triage rule in the self-review remedy guidance: when a finding is
`contract_drift` or `same_document_contradiction` and a single source of truth for the
fact exists elsewhere, the DEFAULT remedy is deletion of the restatement. Correction is
admissible only when the restated fact has no other home — and then the better fix is
usually to give it one.

Corollary worth publishing beside a self-review verdict: a round whose findings were all
resolved by correction is more likely to re-seed than one whose findings were resolved by
deletion. A loop count alone does not distinguish "the surface converged" from "the fixer
kept writing new prose".

## Evidence

- `manage-findings qgate list --plan-id … --phase 6-finalize`: findings cdda73, 44a042,
  24510f, 692ad6
- cdda73 attributes its own defect to commit 926c39548, the previous round's fix
- `status.metadata.phase_steps` `pre-submission-self-review` `firing_count: 8`
