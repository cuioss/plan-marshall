envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:13:26Z

# Early-phase gate quality: init, refine, outline

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 3 lessons. **Suggested fold target:** yours to decide — the three touch
different phases and could be split, but they share one shape.

## The shared shape

Each is a gate whose output **cannot be distinguished from a confident answer** when it in
fact examined nothing, decided nothing, or bound nothing.

## The three instances

| Lesson | Phase | Instance |
|--------|-------|----------|
| `2026-08-26-05-005` | 1-init | The domain detector returned `plan-marshall-plugin-dev` and nothing else, with **zero narrative matches** — resolved purely from the `always_on` leg — on a plan whose realized footprint is **7 of 10 `.py` files**, whose request names `github_pr.py` throughout, and whose Verification section mandates the repo Python build. |
| `2026-08-08-19-007` | 2-refine | A post-clarification re-analysis scored **all six confidence dimensions at 100**, lifting the plan 49.0% → 100.0% in one operator round. The Step 13 check flagged it — which is the check working — but has **no mechanical discriminator** between a genuine 100% and a self-graded one. |
| `2026-08-08-19-008` | 3-outline / 4-plan | The Approach section stated deliverable 1 is the gate and runs first. Deliverable 2 declared `depends=none`. ⛔ **`phase-4-plan` orders tasks from `depends` metadata, never from Approach prose** — so the ordering was inert and the gate gated nothing. |

## What each one teaches beyond its instance

**`2026-08-26-05-005` — the `always_on` leg guarantees a non-empty domain set, which is a
reasonable failsafe and means a zero-match result and a confident single-domain result
produce the identical output shape.** The caller cannot tell "the detector matched this
domain" from "the detector matched nothing and a floor was supplied". ⭐ The lesson points at
the fix this codebase has already used elsewhere: publish the match provenance
(`narrative_matches: N`, and `source: always_on` vs `source: narrative` per domain), the way
`manage-lessons list-stalled` publishes `store_resolution` / `plans_root_state` /
`scanned_plan_count` beside its count. ⚠ Had the operator not been prompted, the plan would
have run with `python` absent from the domain set that governs skill resolution.

**`2026-08-08-19-007` — a 100% score at refine time cannot be validated at refine time.**
⭐ The generalisable part is how this instance *was* resolved: the score was checked against
**downstream evidence** — `phase-3-outline` re-ran the population sweep and the 3-outline
Q-Gate re-derived it a third time, both reproducing it exactly *including corrections to two
counts the original request had wrong*. **Downstream reproduction is the only independent
evidence available for a self-graded score.** ⇒ Have the check name the *evidence class* its
justification rests on — `self-assessment` / `operator-answered` / `downstream-reproduced` —
rather than accepting free prose. Only the latter two are independent.

**`2026-08-08-19-008` — prose reads as a constraint and is consumed by a human reviewer as
one, which is exactly why it survives review. The machine that would enforce it never sees
it.** ⇒ Authoring rule: any ordering claim in an Approach section must be encoded in the
corresponding `depends` field **in the same edit**. Prose may explain an ordering; it may
never be the only place the ordering exists. ⭐ A deterministic Q-Gate candidate follows:
scan Approach narrative for ordering language naming a deliverable, and cross-check for a
corresponding `depends` edge — a prose-asserted edge with no metadata counterpart is a
finding. (This instance was caught by an LLM pass, not a rule.)

⚠ **`2026-08-08-19-008` also records good practice worth preserving**: the fix did not stop
at the flagged field. A symmetric-peer audit of all four `depends` fields confirmed the rest
were correct as authored.

## Claim labels

- **OBSERVED** — all three instances. Each quotes its own gate output or Q-Gate finding id,
  and `26-05-005` additionally corroborates against the realized footprint
  (`git diff 8025b2210^ 8025b2210`).
- **HYPOTHESIS** — that `26-05-005` is a matcher-vocabulary gap rather than a reporting gap.
  ⚠ The lesson itself flags that these are **two different defects needing two different
  fixes** and does not settle which applies. Confirm/refute at the narrative matcher against
  that specific request text. Verify-at-outline.
- **HYPOTHESIS** — that the three belong in one plan. They span three phases and three
  components; this router grouped them by shape, not by surface. Split freely.
