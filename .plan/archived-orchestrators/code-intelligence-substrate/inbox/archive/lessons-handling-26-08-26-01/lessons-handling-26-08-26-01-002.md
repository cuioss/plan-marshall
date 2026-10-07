envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-26T21:14:12Z

# The cost-reducing lane levers fire essentially never, and the checkpoint scores the small end of the bill

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule: this is token-economy, and it is the most directly on-theme lesson
in the drain.

**Cluster:** 1 lesson (`2026-08-08-19-002`) — `standalone`, not folded. **Suggested fold
target:** yours; it may already be held by a staged spec.

## The measurement

`lane-lever-effectiveness` over a **53-plan shipping partition**:

| Class | Target | Over |
|-------|--------|------|
| surgical | 1,200,000 | 1 / 1 |
| single_module | 1,500,000 | 34 / 34 |
| multi_module | 2,500,000 | 14 / 14 |

⭐ **Every classed plan in the corpus is over its armed target.** The four `informational`
rows are the four `broad`-scope plans, which are `unclassed` — no target exists to miss — not
plans that came in under one.

Lever engagement across the same 53 plans:

```text
recipe_routed:            0
minimal_posture_chosen:   0
light_lane_fires:         3
estimated_avoided_tokens: 0
posture_not_taken:        1
```

## The two conclusions, and the second is the one to act on

**1. This is a routing-layer fact, not 49 overspending plans.** ⛔ **A lever that fires zero
times in 53 plans is either unreachable or unarmed, and neither is fixed by moving the
number.** Before tuning targets, establish whether the recipe-match tier and minimal-posture
selection *can fire at all* under current conditions. ⚠ The one plan that did take the light
lane at surgical scope still came in at 2,198,948 against a 1,200,000 target — **lane
selection alone does not close the gap either.**

**2. ⭐⭐ The checkpoint metric measures the wrong end of the bill.** `total_tokens` here is
`input + output` and **excludes `cache_read` / `cache_creation`** — a generation-volume proxy.
The same corpus's `billing-composition` re-derivation puts `cache_read` at **76.2%** and
`output` at **1.1%** of billing weight over all 53 plans (`label: measured`,
`population: 53`).

⇒ **A checkpoint framed on `input + output` is scoring roughly the small end of the bill.
The targets measure generation volume, not cost.** That reframing — not the 49/53 miss count
— is why this routes here.

## The corroborating pair

`cross-check-synthesis` → `surgical_overpay` **fired**: two plans are simultaneously over
their checkpoint and flagged `big_spend_tiny_footprint`:

- `2026-07-28-orchestrator-inbox-pickup` — **4,262,740 tokens over 8 files**
- `2026-07-29-post-merge-review-findings-untriaged-in-main` — **3,797,668 tokens over 3 files**

Those are the clearest lane-lever misses in the corpus: the cheap lane existed precisely to
keep such a plan small.

## Cross-reference to the sibling message

This message pairs with the `run measurement is unrecoverable` cluster also routed to you.
That one records that a 3.5M-token run left **no cost figure at all** — both measurement
paths empty. Together: the corpus can measure generation volume and cannot measure cost, and
the levers meant to reduce cost are scored against the volume metric. ⚠ Check disjointness
before planning against both.

## An artifact caveat about this lesson specifically

⚠ `2026-08-08-19-002` is one of the three YAML-frontmatter lesson files. It enumerates in
`manage-lessons list` with **empty `component`, `category` and `title`** — but unlike its two
siblings its body **is** readable through `get`, which is how this router obtained the
figures above. Its `component` frontmatter says `plan-marshall:phase-1-init`.

⛔ That readability asymmetry is itself unexplained, and it **refutes** the standing
explanation in `2026-08-08-20-002` that YAML frontmatter causes the `not_found`. Filed as an
open defect against this router's own corpus-integrity item; noted here so you know the
figures came from a file the index cannot see.

## Claim labels

- **OBSERVED** — every figure above is quoted from the lesson body, which records them as its
  own `lane-lever-effectiveness` and `billing-composition` aspect outputs over a stated
  population of 53. The `cache_read` 76.2% / `output` 1.1% split carries `label: measured`.
- **OBSERVED** — that the lesson is invisible to the dedup gate (empty `component`), per
  `2026-08-08-20-002` and confirmed first-hand by this router's own `list` output.
- **HYPOTHESIS** — that the levers are *unreachable* rather than merely *unchosen*. The
  lesson poses this as the question to settle and does not settle it. Confirm/refute at
  `phase-1-init` § the Tier 1 recipe-match routing tier and the minimal-posture selection,
  checking whether either can fire under current scoring. Verify-at-outline.
- **HYPOTHESIS** — that the 53-plan partition is still the right population 18 days on. It
  was measured 2026-08-08. Re-derive before quoting the figures forward.
