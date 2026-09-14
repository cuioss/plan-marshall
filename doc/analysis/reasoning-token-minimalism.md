# Reasoning-token minimalism — measurement and decision

An external result reported cutting reasoning tokens ~92% by constraining a
model's visible "thinking" to a five-word ceiling, with task accuracy held and
run-to-run self-disagreement falling from 5.8% to 1.9%. This document is the
measurement-side assessment of whether that lever applies here.

The architectural principle the assessment produced is recorded separately, in
[ADR-021](../adr/021-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc);
this document holds the numbers, the bound they place on the idea, and an
instrument defect found while deriving them.

## Decision

**SKIP.** No reasoning-minimalism rule is added to
`plan-marshall:persona-plan-marshall-agent` or anywhere else. The structural
grounds are ADR-021's; the measurement grounds are below, and they are
independently sufficient.

## Why the reported result does not transfer

The discriminator is the **input:output ratio of the workload a result was
measured on**, and it should be established before any such result is assessed
for transfer.

| | the reported setting | this system |
|---|---|---|
| input per call | a support ticket plus a two-line system prompt | a large context, cached and resident |
| output per call | ~1,800 reasoning tokens | comparatively little |
| dominant term | **output** | **input** — resident context × turns |

Short-prompt, single-shot classification is one of the few regimes where
generation genuinely dominates a bill. Almost every published token-saving
result comes from that regime; almost none comes from long-lived agent contexts.

The reported determinism improvement is a separate claim and is not assessed
here — it is a property of deliberation, which this system controls through
effort levels rather than through prose, and effort reduction is settled on
other grounds.

## The ceiling on a reasoning-side lever

These figures **bound** the idea. They are not offered as a durable measurement:
the corpus percentages they rest on are a single analysis pass that this project
has not re-derived first-party, and the share of generation that is reasoning
rather than tool-call payloads or response text is an estimate, not a measure.
Both would need re-deriving before anything is built on them — which is
precisely why the decision does not rest on them.

Generation is roughly **5%** of billing weight once output's price premium is
applied (see the defect below — the recorded figure understates it fivefold).
Reasoning is a fraction of generation, the remainder being tool-call payloads
and response text. So eliminating reasoning *entirely* caps at low single digits
of spend, and a prose instruction captures only a fraction of its own ceiling —
the reported result's own evidence is that an exhortation achieves roughly
two-thirds of what an enforced ceiling does, in a setting far more favourable to
the exhortation than a line inside a large persona competing with an explicit
effort pin.

The residual sits inside the noise band of ordinary build-time variance, before
subtracting the standing cost of the added line — which loads into every
dispatch and is re-read for the life of each.

## Instrument defect: `billing_weighted_total` understates generation fivefold

`manage-metrics/standards/data-format.md` defines the figure as:

```
input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)
```

`output` is weighted **1×**. Every current Claude model prices output at **5×**
input, so the correction is model-independent. The field is classed
`derived-cost` and rendered as a first-class "Billing (cost)" column, so the
understatement is invisible at every read site.

The consequence is directional, not incidental: every generation-versus-context
conclusion drawn from that column is skewed toward context by a factor of five.
It does not change this decision — the corrected share is still small — but it is
upstream of every token-reduction judgement that reads the column, and is
tracked separately.

A related interpretation trap is worth recording alongside it. A triple of
`cache_read` / `cache_creation` / `output` percentages can be read either as
token shares or as weighted-cost shares, and the readings differ by more than an
order of magnitude. The discriminator is internal: dividing the first two by
their weights must reproduce the independently measured average re-read factor.
Under the cost reading it does; under the token reading it is off by more than
tenfold. **Read the producing formula before interpreting such a percentage.**

## What to do instead

Nothing new. The transferable half of the idea applies to persisted artifacts,
where both directions are already governed — `user-communication.md` Rule 3 for
the orchestrator-to-user leg, `citations-only-return.md` for the sub-agent return
leg. ADR-021 states the principle those two implement, including the
completeness floor that the external result's rule lacks.
