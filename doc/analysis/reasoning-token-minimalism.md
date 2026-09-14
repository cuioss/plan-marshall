# Reasoning-token minimalism in the agent persona — decision

An external result reported cutting reasoning tokens ~92% by constraining a
model's visible "thinking" to five words, with accuracy held and run-to-run
self-disagreement falling from 5.8% to 1.9%. The proposal this document decides
is whether to encode a matching minimalism rule for *thinking* in
`plan-marshall:persona-plan-marshall-agent`.

## Decision

**SKIP.** No thinking-minimalism rule is added to the persona.

The transferable half of the idea is already implemented on the surface that
actually costs money — see [Where the rule already
lives](#where-the-rule-already-lives).

## Rationale

### The dispatch architecture already discards reasoning

A dispatched `execution-context` leaf may think at length and return a bounded
TOON struct; the parent pays for the struct, not the reasoning. The agent
boundary *is* the compressor the external result hand-rolls with a word ceiling.
There is no thinking-token problem left to solve, and the only real knob on
thinking depth is the `execution-context-level-N` effort pin — a different
mechanism with its own measured tradeoff (below).

### The regime does not transfer

The reported result comes from short-prompt, single-shot classification: a
~100-token input against ~1,800 output tokens, so output dominates that bill.
Plan-marshall's regime is the inverse — a large resident context re-read many
times per run, against comparatively little generation. The discriminator when
reading any such result is the **input:output ratio** of the workload it was
measured on.

### Compression advice inverts across the boundary

A persisted artifact is read by a later agent that has no access to the
reasoning that produced it, so it must carry the *derivation*, not the verdict.
A five-word ceiling applied to a persisted surface is a vacuous-authority
generator — a recurring defect archetype in this repository, and the direct
opposite of the standing "derive completeness, never assert it" discipline.

### The rule would be unenforceable

Thinking is not inspectable by a test, a `plugin-doctor` rule, or any CI check,
so compliance could never be observed. The external result's own central claim
is that an enforced ceiling beats a prose exhortation precisely *because* it is
enforced; the enforced version is unavailable here.

### It reduces to "examine less", which is already rejected on measurement

Raising effort levels was measured first-party to cost ~1.34× while moving
per-phase zero-finding rates sharply down (both unraised control phases moved
the other way), establishing that the prior zeros were under-examination. The
standing conclusion is to reject any lever whose mechanism reduces to examining
less, on that ground rather than by weighing it. A "think less" instruction is
that lever under another name, and its downside is asymmetric: not a percentage
of spend, but a defect reaching `main`.

### The line would not pay for itself

`persona-plan-marshall-agent` loads unconditionally into every dispatch, making
it the most expensive place in the corpus to add prose — a byte there is paid on
entry and again on every subsequent turn of every dispatch. Any change to that
file should displace something, not append to it.

## What the arithmetic supports

These figures bound the idea rather than record a durable measurement. The
underlying corpus percentages are a single analysis pass that this project has
not yet re-derived first-party, so they are stated as a ceiling argument, not as
a result to build on.

Generation is roughly 5% of billing weight once output's price premium is
applied. Thinking is only a fraction of generation — the remainder is tool-call
payloads and response text — so the ceiling on eliminating thinking *entirely*
is low single digits of spend, and a prose nudge captures a fraction of that
ceiling. The expected yield sits inside the noise band of ordinary build-time
variance, before accounting for the cost of the added line.

## Where the rule already lives

The version of this idea that pays applies to persisted artifacts, and both
directions are already governed:

- `persona-plan-marshall-agent/standards/user-communication.md` Rule 3 bounds
  the orchestrator-to-user leg: the **completeness floor first** (a failure, a
  skip, or a partial result is outcome and may never be trimmed), then the
  ceiling that cuts narration.
- `ref-workflow-architecture/standards/citations-only-return.md` bounds the
  sub-agent return leg: exactly one TOON block, counts as citations, detail
  persisted to a queryable sink.

Both are enforceable, both sit on the paid surface, and Rule 3 carries the
completeness guard the external result lacks. The residual discipline is
**density, not brevity** — cut bytes that restate, keep every byte that derives.

## Defect surfaced by this analysis

`billing_weighted_total` (see
`manage-metrics/standards/data-format.md`) is defined as
`input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`,
weighting output at 1×. Every current Claude model prices output at 5× input, so
the figure understates generation's share of real spend by that factor while
being rendered as a first-class "Billing (cost)" column and classed
`derived-cost`.

Conclusions drawn from that column about generation versus context are therefore
skewed toward context. This does not change the decision above — the corrected
share is still small — but it is upstream of every token-reduction decision that
reads the column, and is tracked separately.
