envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:36:20Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=medium
rank=10
source_plan=truth-166-architecture-refresh-migration-churn

# An error contract that names the implementing helper is unmatchable by every consumer

## Context

`manage-architecture/standards/client-api.md` documented three error cases in one
sentence. Two named the value a caller can match on — `invalid_ref`, `snapshot_not_found`
— and the third named a Python helper:

    when the current project's `_project.json` is absent, the standard
    `require_project_meta` error envelope.

The handler emits `error: data_not_found` (with `expected_file` and `resolution`). No
caller branching on the `error` field can ever match `require_project_meta`, because that
string is never on the wire. The documented contract is unimplementable as written, and
nothing in the build gate notices: the token is a real symbol, spelled correctly, in a
file whose links and structure are all valid.

Fixed in-run as part of TASK-12, after CodeRabbit reported it (`80d835`, Minor).

## Root cause

The sentence was written from the implementation's vocabulary rather than the consumer's.
The two sibling cases in the SAME sentence were written from the consumer's, so the
document already contained its own counter-example — the inconsistency is visible without
leaving the line.

The general shape: a consumer-facing contract is authored by naming the symbol the author
was looking at. For an error contract the wire value and the helper that produces it are
different strings, so the substitution is silent and total — the doc is not vague about
the error code, it states a different one with full confidence.

## Proposed action

Add a deterministic self-review candidate class: **a documented error condition whose
named token is not a value the component emits**. It is mechanical on both sides —
the doc side is the token in an error-naming sentence, the source side is the set of
`error:` literals the component's handlers write — and the check is set membership. The
strong signal to surface first is an error-naming sentence that mixes both vocabularies,
as this one did: sibling cases named by value with one named by symbol.

Restricting the candidate to a MIXED sentence keeps the class precise and keeps the
population derivable, rather than requiring a judgement about every prose mention of an
error.

## Evidence

- finding `80d835` — CodeRabbit, `client-api.md:1483`, confirmed and fixed in-run;
  "A caller that matches on `require_project_meta` never matches."
- The same sentence's two sibling cases (`invalid_ref`, `snapshot_not_found`) are named
  by value, so the divergence is intra-sentence.
- Four in-house self-review rounds, a clean whole-tree `plugin-doctor` (37 rules, 0
  issues) and a green `verify` did not surface it — no existing rule compares a documented
  error token against the emitted error vocabulary.
- Surface size, honestly bounded: `architecture search --content --literal --pattern
  "Error contract"` returns 10 sites in 5 files (`files_scanned: 2911`, `unreadable[0]`,
  `truncated: false`, `elided[0]`), so the narrow heading-anchored surface is small. That
  sweep does NOT size the broader population of prose sentences naming an error
  condition, which is where the remaining risk sits and which this candidate does not
  claim to have measured.

## Generalizes

The `| Error Code | Cause |` tables every `manage-*` skill carries are safe by table
shape — the column IS the value. The exposure is in PROSE, where an author can name
whatever they were reading. A doc that states a contract in the producer's vocabulary
instead of the consumer's is not imprecise, it is wrong in a way that reads as precise:
the reader gets a specific, confident, unmatchable string.
