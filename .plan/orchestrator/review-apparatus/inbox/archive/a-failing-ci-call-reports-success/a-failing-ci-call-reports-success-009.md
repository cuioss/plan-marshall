envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:49:59Z

# One convention copied into ten docs produced two multi-site defects in two rounds

component: plan-marshall:phase-6-finalize
category: anti-pattern
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

The exit-code convention ("every `python3 .plan/execute-script.py` call carries
this contract") is restated verbatim in the `phase-6-finalize` standards tree
rather than stated once and cross-referenced. Two separate review findings, at two
different HEADs, each found a different defect in that same duplicated paragraph:

- **e33ce8** (HEAD a30871e0) — the exit-0-non-success clause routes the reader to a
  remedy that carries *stderr*, but on that path the diagnostic is on *stdout*, so
  following the clause literally discards the only account of the cause that
  exists. Reported against **10 files**.
- **d760bf** (HEAD 3266ff53) — the three clauses are not a partition: an exit-0
  result with no parseable `status` matches none of them, and the natural fallback
  ("it exited 0, carry on") is exactly the false-green this PR existed to close.
  Reported against **9 files**.

A third, `653ace`, then found that the contract test guarding the widened clause
pins only its bolded heading, so a doc could keep the heading byte-for-byte while
deleting STOP, envelope preservation and stdout synthesis, and the test would
still pass.

## Root cause

A normative contract restated in N copies is an N-site defect the moment it is
wrong, and each copy must be re-edited by hand on every correction. The
duplication also defeats the guard: the contract test pinned a *heading string*
because that is the only thing all ten copies reliably share, which is precisely
why it could not detect the body being gutted.

This is the repository's own "No duplication — cross-reference instead" standard
being violated inside the phase-6-finalize standards tree, and the cost was paid
twice in a single plan — 19 file-edits of remediation across two rounds for one
paragraph.

## Proposed action

State the exit-code convention **once** — a single standards section — and replace
the ten copies with an xref to it, as the surrounding documentation standard
already requires. Then the contract test can assert the full disposition body at
one site instead of a heading substring at ten, which closes `653ace` structurally
rather than by adding a second assertion.

Where a convention genuinely must appear in many docs, generate the copies or
parity-check them against the single source; do not hand-maintain them.

## Evidence

- e33ce8 — `Affects 10 files`, all under `phase-6-finalize/standards/`
- d760bf — `Affects 9 files`, the same paragraph at the next HEAD, closed by TASK-020
- 653ace — `_NEW_CLAUSE` pins only the bolded lead-in; closed by TASK-028
- a1ebb0 records the same paragraph needing hand-reconciliation twice within this run
