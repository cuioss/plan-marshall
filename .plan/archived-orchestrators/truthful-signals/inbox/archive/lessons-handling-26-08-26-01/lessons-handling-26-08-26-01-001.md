envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:11:59Z

# A guard's verdict computed over an empty or unexamined population

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule: not PR/review, not token-economy ⇒ `truthful-signals`.

**Cluster:** 7 lessons. **Suggested fold target:** `PLAN-TRUTH-042` (vacuous guards) if it is
still open; otherwise a new spec. Yours to decide.

## The failure mode

A check returns its passing token over a population it never examined, and the passing token
is byte-identical to the one it returns after a real examination. This is the corpus's
single most-recorded archetype and it has not stopped recurring.

## The seven instances

| Lesson | Instance |
|--------|----------|
| `2026-08-09-22-004` | The standing rule itself: publish the empty population, report `indeterminate`, never a verdict. "The distinction the reader needs is not pass vs fail — it is *looked and found nothing* vs *could not look*." |
| `2026-08-23-20-001` | `review_commitments reconcile` → `verdict: clear`, `commitments_considered: 0`, while six review dispositions were on record. |
| `2026-08-24-08-001` | Same seam, different plan: `deletions_considered: 5`, `commitments_considered: 0`. **And the population is empty BY CONSTRUCTION at that order** — simplify is order 9, create-pr is order 20, so no PR and no review exist yet. The guard as ordered can only ever examine nothing. |
| `2026-08-26-10-001` | Same seam, third plan: `_read_pr_comment_findings` derives commitments from `pr-comment` findings ONLY, so a run reviewed entirely by self-review has an empty population. That run carried 22 findings and 16 applied fixes. |
| `2026-08-24-16-003` | `scope_creep_check` → `residual_count: 0` with `reason: no_baseline_sha`. The zero is a counter that never counted. |
| `2026-08-24-09-002` | `scan_manage_invocation` → `findings: 0`, `population_size: ""`, while four doc-vs-script divergences of exactly its class sat live in the tree it had just scanned. |
| `2026-08-26-06-003` | 33 of 37 plugin-doctor rules report `findings: 0` with an empty `population_size`. The 4 that DO report include `analyze_argument_naming` at 2805 with **304 blind spots** — a zero over ~89% coverage, legible only because that one rule fills the columns in. |

## What makes this cluster worth one plan rather than seven

⭐ **Three of the seven are the same seam** (`review_commitments reconcile`) hit on three
different plans with three *different* empty-population causes: no dispositions anchored,
empty-by-order, and wrong-producer-filter. A fix that addresses one cause leaves the other
two live. The three together are the argument for fixing the seam's *reporting* — a distinct
verdict token for the empty case — rather than any one population.

⭐ **`2026-08-24-09-002` and `2026-08-26-06-003` are the same defect at two scales**: a rule
that guards a set and does not publish the set's size. The second measures the blast radius
at 33 of 37 rules, which makes it a roster-wide remediation rather than a per-rule fix.

## Claim labels

- **OBSERVED** — every instance above is quoted from a lesson body recording a live run;
  the figures (`commitments_considered: 0`, 33 of 37, 304 of 2805) are the filing plans'
  own measurements.
- **HYPOTHESIS** — that a single reporting change (a distinct empty-population verdict
  token) addresses all three `review_commitments` instances. Confirm/refute at
  `phase-6-finalize/scripts/review_commitments.py` § `_read_pr_comment_findings` and its
  verdict-emitting return. Verify-at-outline.
- **HYPOTHESIS** — that PR #1340's `population_size` / `blind_spots` columns are the right
  vehicle for the plugin-doctor roster fix. Confirm/refute at
  `pm-plugin-development/skills/plugin-doctor` § the rule-result schema. Verify-at-outline.

⛔ **Counts in this message are the filing plans' own and were NOT re-derived by this
router.** Treat them as a sample of the corpus, not an enumeration of it.
