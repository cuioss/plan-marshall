# Citations-Only Return Shape

The single source of truth for the return shape every **read-only dispatch** uses: the envelope returns one TOON summary and persists its detail to a structured sink, emitting no free prose.

A read-only dispatch is a dispatched envelope whose deliverable is *judgement over content it reads* — an analysis, a classification, a survey, an assessment sweep — as opposed to an envelope that mutates the working tree. Its findings are the product; its narrative is not. This standard governs the shape in which that product comes back.

## The rule

A read-only dispatch returns **exactly one TOON block and nothing else**. No prose preamble, no per-item narration, no restated reasoning, no closing summary paragraph, no markdown headings around the block. The TOON carries status, counts, and the single bounded `display_detail` routing field — nothing further.

`display_detail` is the marketplace-wide agent-return-shape convention (≤80 chars, ASCII, no trailing period; owned by [`agents.md`](agents.md)): one routing summary the orchestrator surfaces without opening the sink. It is **permitted, not an exception** — its hard length bound is what keeps it a citation rather than a retelling, so it cannot grow into the prose this rule eliminates. Everything the prohibition names above stays prohibited whether it appears in the block or around it: per-item narration, restated reasoning, and closing prose paragraphs are excluded regardless of which field would carry them.

The counts are **citations**, not the content: they tell the caller how many records were written and where to look, and the caller retrieves the detail from the sink by query. A caller that needs an individual item reads it from the sink; it never parses it out of the return.

This is a return-shape economy rule. A dispatched read-only envelope has already paid to read its inputs; re-emitting a natural-language retelling of what it read is a second full payment for content the sink already holds verbatim, and the retelling is the copy that goes stale. Prose in the return is therefore not merely redundant — it is the copy most likely to disagree with the sink.

## Sink-persistence obligation

The counts in the return are only meaningful because the detail is somewhere else. Every applying dispatch site MUST therefore satisfy all four of the following:

1. **Persist before returning.** Each item's detail is written to the sink at the moment it is produced — not batched at the end, and never held only in the model's context. An envelope that ends without having persisted an item it counts has produced nothing retrievable for that item.
2. **Persist through a script.** The sink is written via a `manage-*` script call (e.g. `manage-findings assessment add`), never by authoring a report file and never by direct `.plan/` file access.
3. **Persist to a structured, queryable sink.** A JSONL/TOON record store the caller can query by field. A free-prose `.md` report is not a sink — it moves the prose rather than eliminating it.
4. **Keep the return reconcilable with the sink.** Every count the return emits must correspond to persisted records, so a caller can verify the return against the store rather than trusting it.

## Applies to

Each row names one dispatch site that applies this standard. A site joins the roster only where the standard *pays* — it already returns a summary and persists its detail to a structured sink. This roster is the authoritative population: the conformance detector derives its subjects from these rows, so adding a conforming site here is picked up with no detector edit.

- `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/component-analysis-contract.md` — the component-analysis workflow contract. Its dispatched envelope classifies each supplied component file and persists every assessment via `manage-findings assessment add`; the return carries the per-certainty counts only.

## Out of scope

**`execution-context-reader`'s untrusted-ingestion boundary is explicitly NOT governed by this standard.** The reader variant also returns a constrained struct, but for an unrelated reason: it contains untrusted external bytes so a deterministic validator can clamp them before any consumer sees them. That boundary is about **containment of untrusted content**; this standard is about **return-shape economy** for content the envelope already trusts. The two constraints happen to rhyme in shape and must not be merged — folding the reader into this roster would make a security boundary look like a cost optimization, and a future relaxation of the cost rule would silently relax the containment rule with it. See `plan-marshall:untrusted-ingestion` for that boundary.

A dispatch that mutates the working tree is likewise out of scope. Its return reports what it changed, and its detail lives in the diff and the change ledger — a different sink with a different retrieval path.
