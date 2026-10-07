envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:56:19Z

component=plan-marshall:phase-6-finalize
category=bug
proposed_title=Doc-contract contradiction: dispatch-inline-split.md classifies architecture-refresh as DISPATCHED, two other docs say INLINE

# Doc-contract contradiction: `dispatch-inline-split.md` classifies `architecture-refresh` as DISPATCHED, two other docs say INLINE

## Status

Found during `lane-router-reads-the-wrong-body`. Not fixed (out of scope). Cheap to resolve, but needs a decision on which side is right.

## The contradiction

Three documents describe the execution mode of the `default:architecture-refresh` finalize step:

| Document | Says | Authority |
|----------|------|-----------|
| `dispatch-inline-split.md` | **DISPATCHED** | Declares itself the **single source of truth** for the dispatch/inline split |
| `phase-6-finalize/SKILL.md` | **INLINE** (present in the inline-only list) | Consumer |
| `architecture-refresh.md` | **INLINE** ("This step is **inline**") | The step's own body |

**2-vs-1 against the declared authority.**

## Why it matters

This is the `doc-contract-divergence` archetype in its most awkward form: the divergence is *between* a document that claims sole authority and the two documents that actually govern behaviour. That means:

- a reader who follows the declared source of truth gets the wrong answer;
- a reader who follows the step body gets the right answer but has violated the stated authority hierarchy;
- and there is **no test** that reads the split doc and cross-checks it against the step frontmatter, so the divergence is invisible to CI.

The majority is not automatically correct — the split doc might be right and the other two might be stale. But a self-declared single source of truth that disagrees with the behaviour it describes is worse than having no such declaration.

## The rule (candidate)

1. **Resolve the contradiction by observing the runtime**, not by counting documents. Determine whether `architecture-refresh` actually runs inline or dispatched in this run (this plan's finalize recorded it with `display_detail: "no module structure changed"`), then correct whichever docs are wrong.
2. **Derive the split, do not restate it.** A "single source of truth" table that is hand-maintained alongside per-step frontmatter will drift. The dispatch/inline classification should be **derived from the step frontmatter** (or validated against it by a `plugin-doctor` rule), so a divergence is a build failure rather than a reading discrepancy.
3. Recurrence note: this same field was previously observed carrying an **architecture-refresh dual classification** — it is the second time this exact step has been the subject of a classification divergence.

## Detection

A structural check that, for every finalize step, compares its classification in `dispatch-inline-split.md` against its own frontmatter and against `phase-6-finalize/SKILL.md`'s inline-only list. Any disagreement fails.
