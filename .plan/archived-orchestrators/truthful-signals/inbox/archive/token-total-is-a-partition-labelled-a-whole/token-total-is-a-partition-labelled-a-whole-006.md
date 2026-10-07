envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:35:01Z

component=plan-marshall:manage-metrics
category=anti-pattern
bundle=plan-marshall

# A default's rationale must be scoped to the population that actually reaches it, not to the case that motivated it

## What was observed

A missing `total_tokens_population` reads as `dispatched`. The justification written into `standards/data-format.md` and repeated in `_token_population`'s docstring was:

> *a row that was never enriched can only have been filled from dispatched sources*

The claim is true of a never-enriched row. It is false of the population that actually reaches the default. An archived plan enriched by the **pre-labelling** `enrich` already took the inline fold into `total_tokens` and carries no discriminator. Its inline `1-init` row therefore renders unmarked as `dispatched`, and its Total is never marked `(spans populations)` — a main-context measurement presented under a dispatched label, which is the exact defect this plan exists to remove, surviving in the historical corpus.

So `absent` covers two structurally different rows:

| Row | What the default does |
|-----|-----------------------|
| never enriched | exact — no fold ever happened |
| enriched by a pre-labelling `enrich` | **under-reports** — the fold already happened and is now invisible |

The default itself is correct and was kept. No discriminator can be recovered without re-enriching a transcript that is usually gone. What was wrong was the *rationale*, which asserted exactness over a set wider than the set it described.

## How it was dispositioned

Narrowed rather than accepted. Both sites now state that absent-reads-as-dispatched is the **best available default and not a guarantee**, name both rows that reach it, and state the second case as unrecoverable and accepted rather than guessed at. Go-forward rows are always stamped.

## The generalisable rule

**When you write a default, name the population that reaches it — not the case you had in mind.** The two diverge whenever a format changes: every record written before the discriminator existed lands in the default bucket, and it lands there for a completely different reason than the case the default was designed for.

Diagnostic question, cheap to ask at authoring time: *"what else, other than the case I am thinking of, produces an absent value here?"* For any newly-added field the answer is always **the entire pre-existing corpus**, and that corpus was not necessarily produced by the process the default assumes.

Corollary: a rationale that says *"X can only have come from Y"* is an exhaustiveness claim. Exhaustiveness claims about a data population need the same treatment as exhaustiveness claims about a code enumeration — re-check against the declaring source, and count the corpus rather than reasoning about the intended case.

## Impact

Applies to every `absent → default` read in the metrics surface and to any future field added to a persisted record with historical rows. Direct epic-theme fit: the original wording was a confidently-scoped claim wider than its evidence, and its confidence was doing real work — it was the stated reason no one needed to look at the legacy corpus.
