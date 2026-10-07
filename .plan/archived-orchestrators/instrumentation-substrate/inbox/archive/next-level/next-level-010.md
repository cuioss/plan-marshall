envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:43:49Z

## The lessons corpus has no provenance model and no quality measurement

Source: Day 3 whitepaper (see message 009 for provenance and the applicability caveat). The second of its two
sections that bear on us.

### Trust derived from source, not asserted

The paper grounds a memory's trustworthiness in its **provenance** — origin and freshness — and ranks source
types explicitly:

- **Bootstrapped data** (pre-loaded from internal systems): high trust.
- **User input**: explicit (a form) is high trust; implicitly extracted from conversation is lower.
- **Tool output**: "Generating memories from Tool Output is generally discouraged because these memories tend
  to be brittle and stale, making this source type better suited for short-term caching."

⛔ That last line is the uncomfortable one. A large share of our lessons corpus is derived from exactly that —
observed tool returns, run artifacts, build and CI output — which the paper puts in its lowest-trust,
explicitly-discouraged class. Our own record corroborates the failure mode rather than the paper: recalled
entries that were accurate when written and silently decayed, and a standing discipline of verifying a named
file or flag still exists before acting on a remembered claim. That discipline exists *because* the corpus has
no freshness model; the verification is done by hand, per recall, forever.

The paper's remedy is a confidence score that **moves**: raised by corroboration across sources, lowered by
age and by contradiction, with pruning triggered by time-decay, by never-corroborated low confidence, or by
irrelevance. We have `status` and tombstones — a lesson is live or retired. There is no position between them.

### A better deletion primitive than the one we use

On removing data derived from a withdrawn source:

> "Deleting every memory 'touched' by that source can be overly aggressive. A more precise, though
> computationally expensive, approach is to regenerate the affected memories from scratch using only the
> remaining, valid sources."

Our current move for a partially-covered lesson is to **trim** it. Trimming edits a conclusion in place while
leaving its unstated derivation intact — which is how a lesson ends up asserting something its surviving
sources no longer support. Regeneration from surviving sources is a different primitive with a different
failure mode, and it is the one that matches this epic's derive-don't-assert discipline.

### The measurement vocabulary we lack

The paper's memory-evaluation section supplies a population-derived quality frame, scored against a manually
built "golden set":

- **Precision** — of the memories created, what share are accurate and relevant. It guards specifically
  against "an over-eager memory system that pollutes the knowledge base with irrelevant noise."
- **Recall** — of what should have been captured, what share was.
- **F1** as the balance, plus **Recall@K** for retrieval and an end-to-end task-success judge for whether the
  memory helped at all.

Nobody has ever measured our corpus on any of these. A precision number would answer a question this epic
cares about directly — how much of the substrate is noise that costs tokens on every call and changes no
behaviour — and it is the same shape as the derived-completeness discipline already required here: scored
against an enumerated golden set, publishing its population.

### Bounds

- No data. The paper describes patterns for conversational memory products; none of its numbers are ours.
- A golden set is human labour, and its cost must be sized before it is staged — see message 005 on what
  happens when a verification layer's cost is not bounded at design time.
- Routing: adjacent to the lessons-handling epics; the orchestrator's call.

### Status

Names two absent mechanisms (moving confidence, regeneration-over-trim) and one absent measurement
(precision against a golden set). Decides nothing.
