envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:55:35Z

component=plan-marshall:manage-references
category=bug
proposed_title=scope_estimate has four writers, two incompatible vocabularies, two meanings of "surgical", no provenance, no enum validation

# `scope_estimate` has four writers, two incompatible vocabularies, two meanings of "surgical", no provenance, no enum validation

## Status

**Found during `lane-router-reads-the-wrong-body`, deliberately NOT fixed.** Structural, and a precondition for trusting anything downstream of `scope_estimate`.

## The finding

Four writers of `scope_estimate` were enumerated (via `git grep` sweep — the fourth, at `phase-3-outline/workflow/light-lane.md:126`, was missed by the first pass; see the coverage-gap message):

They use **TWO INCOMPATIBLE VOCABULARIES**:

- a **2-value** vocabulary, and
- a **5-value** vocabulary,

with **two different meanings of `surgical`** between them. There is:

- **no provenance marker** on the persisted value — a reader cannot tell which writer produced it, therefore cannot tell which vocabulary it is in, therefore cannot interpret it;
- **no enum validation in `cmd_set`** — any string persists successfully.

## Why it matters

This is a **producerless / producer-mismatch** field in the exact sense the epic has catalogued before. The consumer (the lane router) reads a bare string and branches on it. When the string came from the other vocabulary, the branch is silently wrong — and because there is no validation, there is no error, no warning, and no way to detect the mismatch after the fact.

It also makes every downstream investigation harder: the live `surgical` vs `single_module` divergence in this same plan cannot be fully diagnosed *because* provenance is absent.

The confident-signal shape: `scope_estimate: surgical` reads as a definite, meaningful classification. It is actually ambiguous between two schemes.

## The rule (candidate)

1. **One vocabulary.** Collapse to a single enum. If both granularities are genuinely needed, they are two fields, not one field with two meanings.
2. **Validate at the write boundary.** `cmd_set` must reject an out-of-enum `scope_estimate`. A field with no validation is a field with no contract.
3. **Stamp provenance.** Persist the writing component alongside the value, so a divergence is attributable rather than undetermined.
4. **Population-derive the writer set** before declaring the sweep complete — a hand-listed set of writers is a sample.

## Ordering note

This should land **before or with** any fix to the refine/outline divergence, since that diagnosis depends on provenance existing.
