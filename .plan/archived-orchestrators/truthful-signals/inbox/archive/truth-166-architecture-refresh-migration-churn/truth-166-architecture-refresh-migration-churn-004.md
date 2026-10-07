envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:19Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
rank=4
source_plan=truth-166-architecture-refresh-migration-churn

# Bind the no-flush-left-multiline rule to fragment PRODUCERS, not just fragment authors

## Context

`references/chat-history-analysis.md` states a MUST for fragment bodies: no `|` block
scalars, and multi-line content must be a quoted scalar, because "any continuation line
that sits flush at column 0 and contains a colon is re-parsed by `parse_toon` as a
phantom sibling top-level key, leaking a spurious aspect into the bundle."

The skill's own `extract-chat-signal` pre-pass violates that rule on the very field the
Tier-1 path consumes. Its `reduced_transcript` value opens as a quoted scalar and then
continues with flush-left lines containing colons — `operator-decision:`, `user:`,
`<command-name>/plan-marshall: plan-marshall</command-name>` — so `parse_toon` takes only
the first line and re-reads the rest as phantom top-level keys.

Compounding it, the record declares `reduced_bytes: 298684` while the emitted field
carries roughly 2.6KB, about 0.9% of the measured reduction.

## Root cause

The serialization discipline was written for the hand-authored fragment path and enforced
there, while the script that emits the same field shape was left unguarded. Separately,
`reduced_bytes` measures the reduction rather than the payload actually handed over, so
the two fields sit adjacent and describe different quantities.

## Proposed action

Emit `reduced_transcript` as a quoted scalar with escaped newlines — the rule the sibling
contract already states — or hand back a file path instead of an inline payload. Make
`reduced_bytes` describe the delivered payload. Extend the MUST in
`chat-history-analysis.md` to cover producers, not only fragment authors.

## Evidence

- contract: `references/chat-history-analysis.md:97` — the MUST-NOT this output violates.
- observed: `extract-chat-signal run` output lines 7-12 — a quoted opening followed by
  five flush-left continuation lines, three of which contain a colon.
- observed: `reduced_bytes: 298684` beside a delivered payload of roughly 2.6KB.
- Tier-1 was correctly selected (`no_signal: false`, `over_budget: false`,
  `status: success`, `reduced_turn_count: 44`) — every discriminator read healthy while
  the payload behind the gate was absent.

## Generalizes

A serialization rule written only for hand-authored artifacts leaves the scripts emitting
the same field shape unguarded, and the script path is the one that runs every time.
There is a second, structural gap behind it: the closed skip-token set
(`transcript_too_large` / `transcript_unavailable`) has no token for "delivered
truncated", so a consumer must either fabricate analysis from the fragment it got or
mislabel the cause as one of the two it did not have.
