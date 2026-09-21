envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:33:34Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
bundle=pm-plugin-development

# Three self-review passes each found "the last site" and each was wrong — a fix is not closure until the population is enumerated

## What was observed

`pre-submission-self-review` fired three consecutive times on PLAN-TRUTH-035 and found **exactly one real defect on each firing**. That is not three independent finds. It is one doc cascade that the first three passes each mis-scoped, each time asserting a closure it had not verified.

The cascade was a single claim — *what triggers `inline_main_context_tokens`* — mirrored across four sites. The live code writes the field only when `_inline_main_context_sum` is truthy, and that sum is the three-field `input + output + cache_creation` derivation which **excludes** `cache_read_input_tokens`. Every stale site said "non-zero four-field usage".

| Pass | Sites known | Sites actually live | Claim made |
|------|-------------|---------------------|------------|
| CodeRabbit (`2ec3e0`) | 2 → 3 | 4 | "Three documentation sites overstate the trigger" |
| Self-review (`3cb5d8`) | 3 | 4 | commit `4e95e3af1` "corrected exactly this trigger wording" in two docs — left `SKILL.md` on the pre-correction claim |
| Self-review (`820969`) | 4 | 4 | the fourth site was the **signature table 18 lines below prose the previous pass had just corrected in the same file** |

The fourth site is the damning one: `data-format.md` lines 278-279 still named "non-zero four-field usage" as the Condition, while lines 257-260 of the *same document* had already been rewritten to the corrected form. A pass had edited that file and declared the cascade closed without re-reading the rest of it. And that section is the one every sibling doc cross-references as the authority.

A fourth finding in the same family (`897f6b`) landed the same day: `data-format.md` line 271 heads a subsection **"Two signatures, one derivation, always labelled"** over a table whose own `Signature` column carries **three** rows, while `record-metrics.md` cross-references that exact section for *"the three signatures"*. Same failure mode: a count asserted in prose, never re-derived from the thing it counts.

Only the final pass enumerated the population — `git log -S` over the claim string — instead of sampling. That pass found nothing further, and that is the only "nothing further" in the sequence that carries any weight.

## The bitter part

This plan **shipped the rule that would have prevented this**, into `persona-plan-marshall-agent/standards/agent-behavior-rules.md`:

> *Never assert closure over an enumeration without re-checking it against its declaring source.*

The plan then violated that rule three times while writing it. Worse, one of its own Q-Gate findings (`deeafd`) observed that the rule's *"mirrored at several sites in one document"* scoping was already too narrow — the cascade it was written from crossed document boundaries.

## The generalisable rule

**"I fixed the other sites" is a claim about a set, and a claim about a set requires enumerating the set.** Reading the sites you already know about and finding them consistent is a sample, not a census — it can only ever confirm the sites you started with.

Operational form:

1. When a fix touches a claim that could be mirrored, derive the site list **mechanically** from the claim's text (`git log -S`, `grep` of the distinctive phrase) before declaring closure. Do this on pass one, not pass four.
2. **Re-read the whole file you just edited.** Site four was in the same document, 18 lines from an edit that had just been made. Same-document mirrors are the easiest to miss precisely because the file feels handled.
3. **A count stated in prose is a mirror of the thing it counts.** "Two signatures" over a three-row table, "all three sites" over a five-site mirror set, "27 live pairs" where the arithmetic gives 31 — all three shapes appeared in this one plan. Any narrative number is a mirror and must be re-derived, not carried forward.

## Impact

Applies to every doc-contract change in the marketplace. The cost here was three extra self-review rounds and three extra commits on a 13-task plan, all of which reported success. The pattern registers as *n consecutive green-then-defect cycles*, which is a measurable signature: **a self-review that finds exactly one defect per firing, repeatedly, is not converging — it is sampling.** That signature is worth detecting directly.
