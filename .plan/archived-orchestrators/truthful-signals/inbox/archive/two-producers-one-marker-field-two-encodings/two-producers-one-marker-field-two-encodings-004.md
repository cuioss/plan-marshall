envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:56:14Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=review-apparatus
delegation_note=PR/review-shaped — belongs to review-apparatus under the standing three-way routing rule. Emitted here because a dispatched leaf writes only to the epic it was dispatched under; forward via the inbox channel rather than a direct edit.
relates_to=lesson-2026-08-08-20-001 cross-cutting guard_unmatched remedy

# review_completeness collapses a rejected participation pair into the same absent state as real silence

## Context

`review_completeness check` admits `--participated-bots` entries only as
`bot_kind:evidence_kind` pairs whose `evidence_kind` is one of that bot's declared
`participation_evidence` publish shapes. That rejection rule is correct and is
documented in the flag's own help text: *"a bare bot_kind with no evidence_kind is
rejected, because unqualified presence does not prove a bot reviewed this diff."*

The rejection is never reported. Driving the shipped verb over the same plan with
three inputs that differ only in the evidence term:

| `--participated-bots` | `coderabbit` state | exit | status |
|---|---|---|---|
| `coderabbit:inline` (declared shape) | `participated` | 0 | success |
| `coderabbit` (bare kind) | `absent` | 0 | success |
| `coderabbit:review_comment` (undeclared shape) | `absent` | 0 | success |

Rows 2 and 3 are rejections. Row 3 would also be a rejection if `coderabbit` were
misspelled, or if the bot's declared shapes changed under a caller that still passes
the old term. All three produce output byte-identical in the fields a caller reads:
`state: absent`, no diagnostic, exit 0.

So a caller typo, a stale evidence vocabulary, and a bot that genuinely published
nothing are one observation.

## Root cause

The verb has three input classes — admitted, rejected-as-malformed, and
absent-from-the-list — and two output states. The rejected class is folded into
`absent`, which is a *measured* claim about the bot's behaviour, on evidence that was
discarded rather than gathered.

The direction of the fold matters differently on the two bot lists:

- On `--required-bots`, `absent` blocks. A typo produces a false block — noisy but
  fail-closed.
- On `--optional-bots`, `absent` is reported as a non-participating reviewer and
  never blocks. A typo there manufactures a silent bot, which is precisely the
  evidence a maintainer would use to drop a reviewer. This PR's own review
  retrospective closes on exactly that hazard: Sourcery "contributed nothing to the
  ledger and looks worthless in the metrics table", while having produced the only
  observations no other reviewer made.

This is the cross-cutting remedy lesson `2026-08-08-20-001` already names —
*"a check whose guard set does not match its source should be able to say so ... a
`guard_unmatched` outcome distinct from `not_applicable` would have surfaced all
four"* — needing a second home in a component that lesson does not cover.

## Proposed action

- Emit `rejected_participation_pairs[]` naming every input that failed admission and
  the reason (`bare_kind`, `unknown_evidence_kind`, `unknown_bot_kind`), so a caller
  can distinguish a malformed argument from a measured gap.
- Give a bot whose only evidence was rejected a state of its own —
  `evidence_unrecognised` — distinct from `absent`. `absent` should mean *the
  provider was consulted and this bot published nothing*, never *the caller's input
  did not parse*.
- Add a matched control pair pinning both arms: an admitted pair must yield
  `participated`, and a rejected pair must yield the new state and populate
  `rejected_participation_pairs[]`. A guard that has never been observed to fire on
  its rejection path is the archetype this repository tracks.

## Evidence

- first-party, driving the shipped verb three times against plan
  `two-producers-one-marker-field-two-encodings` with `--required-bots pr-agent
  --optional-bots coderabbit,sourcery`, varying only `--participated-bots`:
  `coderabbit:inline` → `coderabbit,participated`; `coderabbit` →
  `coderabbit,absent`; `coderabbit:review_comment` → `coderabbit,absent`. All three
  `status: success`, exit 0, no field naming a rejected input.
- `bot_registry.py` data-block schema — coderabbit declares
  `participation_evidence: [review_body, inline]`, so `review_comment` is
  undeclared and correctly refused
- `review_completeness check --help` — documents the rejection rule but specifies no
  reporting of it
- artifact: `review-retrospective.md` § Comparative Verdict — the concrete cost of
  reading an unmeasured silence as a measured one
- lesson `2026-08-08-20-001` § Proposed action, cross-cutting bullet — the
  `guard_unmatched` remedy this instance needs
