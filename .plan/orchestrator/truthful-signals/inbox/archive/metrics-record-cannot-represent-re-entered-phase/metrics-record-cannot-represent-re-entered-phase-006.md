envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:03:21Z

# Candidate lesson: a document that both forbids and mandates restating its own schema — same-document contradiction, twice in one file

**Source**: Q-Gate findings `694669` and `7528a6` (6-finalize), both `fixed`
**Defect class**: same_document_contradiction
**Surface**: `manage-metrics/standards/data-format.md`

## Instance 1 — "consumers do not restate" vs "four surfaces MUST move in lock-step"

Within one section, two statements about the same files contradicted each other:

- `:777` (pre-existing) — consumers "reference this section rather than restating the schema",
  naming the `manage-metrics` writer, the `plan-retrospective` `analyze-logs.py` reader, and
  SKILL.md.
- `:811` (added by this plan) — four surfaces **restate it and MUST move together**, naming three
  of those same files plus the hand-copied `_BC_LEDGER_COLUMNS` tuple in `.claude/…/audit.py`.

Both cannot be true. The failure mode is asymmetric and that is the point: **a maintainer who
reads `:777` first concludes there is nothing to keep in sync** — which is precisely the drift the
new lock-step obligation exists to prevent. And the fourth surface is the one `:811` itself flags
as invisible to a content sweep, because `.claude` is not crawled by the architecture inventory.

Resolution direction matters here. It was resolved **in favour of `:811`, because `:811` is what
is TRUE of the code** — verified by reading all four surfaces. They each cite the section as
authority and restate part of the schema anyway, because they run in separate processes and
cannot import a shared constant. The honest doc says that, rather than asserting a
single-source-of-truth that the process boundary makes impossible.

## Instance 2 — "has a documented absent-reads-as default" vs "Absent reads as: nothing"

`:505` said the new `{denominator}_sampling_point` discriminator has the same shape as
`total_tokens_population` and `value_scope`, enumerating that shape as three attributes including
"a documented absent-reads-as default". Eight lines later, `:513` stated in bold:
**"Absent reads as: nothing. There is no default."**

A reader asking what an absent `deliverable_count_sampling_point` means got two answers from one
section. The sibling surface (`manage-metrics` SKILL.md:147) had already resolved it in the
opposite direction — "There is no absent-reads-as default here" — so `:505` also contradicted the
restating surface it governs.

## The generalizable shape

Both instances share a mechanism: **an analogy sentence ("this has the same shape as X") that
carries over more attributes than are actually true.** Two of the three attributes carried over;
the third did not, and the sentence asserted all three. Analogy is a compression device, and it
compresses away exactly the exception that matters.

## Candidate rule

> When documenting a new field "by analogy" to an existing one, enumerate which attributes carry
> over AND which do not. An unqualified "same shape as X" is a claim about every attribute of X.

> Adding a lock-step / must-move-together obligation to a document obliges you to re-read that
> document for pre-existing statements that the obligation contradicts — most often a
> "consumers do not duplicate this" line written before the duplication became necessary.
