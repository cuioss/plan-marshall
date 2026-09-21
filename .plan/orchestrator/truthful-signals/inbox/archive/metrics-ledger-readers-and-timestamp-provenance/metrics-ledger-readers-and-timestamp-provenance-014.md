envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:12:38Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Verify a review finding before ACTING on it, not only before rejecting it

## Context

A review finding on this plan proposed deriving `_CANONICAL_COLUMNS` in
`plan-retrospective/scripts/analyze-logs.py` from the current dispatch-boundary writer
contract, so that the two could not drift apart.

The remedy is plausible, well motivated, and would have broken the reader.
`_CANONICAL_COLUMNS` is not a mirror of the current writer. It is the fallback that
`_parse_dispatch_boundary_file` uses ONLY when a boundary file declares no `rows` header —
that is, when decoding a FROZEN legacy positional layout. Every column in a header-bearing
file is already resolved BY NAME through `_cell_by_name`. Deriving the constant from the
live writer contract would have re-pointed the legacy decoder at today's column order and
silently mis-decoded every historical file, on the one surface whose entire purpose is that
it does not move.

The proposal was checked against the code and declined with that reason.

## Root cause

Triage discipline here is well developed on the REJECTION side: a finding is not dismissed
without verification. The ACCEPTANCE side carries no equivalent requirement.

But a finding's diagnosis and its prescription have independent truth values. This one was
correct about the risk (two things can drift) and wrong about the mechanism (they are not
supposed to agree). Only the diagnosis is what the reviewer actually observed; the
prescription is the reviewer's inference, and it inherits none of the diagnosis's evidence.

Acceptance is also the cheaper-looking path — it produces a diff, closes the comment, and
reads as responsiveness — so the asymmetry is self-reinforcing.

## Proposed action

- Make the triage contract symmetric: a `fixed` resolution must record what was verified
  about the REMEDY, not only that the finding was real. Today a `fixed` finding's
  `resolution_detail` typically reads "evidenced by landed change {sha}", which evidences
  that something changed, not that the change was correct.
- Where a finding proposes unifying two constants, the specific acceptance check is: are
  these two things INTENDED to be equal? A deliberately frozen legacy decoder is the
  standard counter-example, and a compatibility shim is the second.

## Evidence

- `analyze-logs.py` — `_parse_dispatch_boundary_file`, `_cell_by_name`,
  `_CANONICAL_COLUMNS`
- corroborated by this plan's own finding `965e9a`, which independently documents the
  by-name-with-positional-fallback resolution rule and the headerless-file case
- the review proposal and its decline
