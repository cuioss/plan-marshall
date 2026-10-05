# Landing Analysis: PLAN-PRQ-15 — Project aggregate, identity fields, and a skill layout with one front door

epic: post-run-quality
workstream: WS-05
pr: none — `cuioss/plan-marshall-telemetry` is main-only by design; landed as 8 commits,
`0965060..0adc341`, head `0adc341`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground
> truth — a pasted claim is a lead, never a fact.

⭐ **All seven deliverables shipped, and the run found a defect in `PLAN-PRQ-13`.** Second consecutive
landing in the out-of-lifecycle lane, and the second whose self-review did more than this epic's
bot-reviewed PRs typically do.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence (verified first-party) |
|---|---|---|
| D0 — gate: confirm the three gaps, settle the naming collision | **shipped, all three confirmed** | run report § D0; the collision was resolved by naming the field `completion`, not `state` |
| D1 — repository identity | shipped | 60 of 70 plans log `Created PR #N: <url>`; `--source-repo`'s remote covers all 70 |
| D2 — PR URLs | shipped | built only once the repository is known; `url: null` with a reason otherwise |
| D3 — completion state | shipped | 63 `fully_implemented`, 3 `partially_implemented`, **0 `aborted`**, 4 `indeterminate` over the real corpus |
| D4 — project-level AsciiDoc aggregate | shipped | `reports/{slug}/project-report.adoc`, regenerated on every default engine run |
| D5 — controls | shipped | incomplete-population-renders-as-floor controls green; new roll-up agreement control |
| D6 — skill layout, three parts | **shipped, in the required order** | commits `bec1e7d` (a) → `b22de0c` (b) → `a0af495` (c), the rename last and alone |

**D6 verified in the tree, not taken on trust:**

- `.claude/skills/` now holds exactly `analysis-engine`, `analyze`, `transfer` — `era-stamp-fill` is gone,
  folded in.
- `test/` holds `analysis-engine/`, `analyze/`, `transfer/`. ⭐ **The mirror held, and it got stronger**:
  `test/analyze/` is NEW, carrying the control that fails if a slash-command usage example comes back.
- The rename commit shows **126 rename-detected paths** — `git mv`, both trees in one move, exactly as D6
  required.
- The engine's frontmatter reads `user-invocable: false`. `analyze` is the only way in.
- ✅ **The rename is complete.** The old name survives in exactly two files, both correctly: the PRQ-13 run
  report (a historical record) and the PRQ-15 run report (which documents the rename and must name it).

## The run corrected my blast-radius figure, and the correction is instructive

I measured **46 occurrences across 15 files**; the rename was **38 across 14**. ⚠ **My figure was correct
when taken and stale by the time it was used** — I measured before D6(b), and folding `era-stamp-fill` into
the engine removed some references on the way. ⭐ **The lesson is about ordering, not arithmetic**: a blast
radius measured against the tree *before* an earlier deliverable runs is a moving figure, and a spec that
quotes one should say which step it was measured at. Mine did not.

## `aborted` is reachable but has never occurred — and that distinction was preserved

⭐ **This is the honest-zero rule applied to a vocabulary value, and it is the result I most wanted to see.**
D3 established that `aborted` is derivable only from an explicit abandonment record —
`metadata.archived_reason` holding anything other than `normal_completion`. Of 70 archived plans, **none has
one**; the 7 that record a reason all say `normal_completion`.

So the value is **producible but never produced**, which is a different fact from unreachable, and
different again from "no plan was ever aborted" — the archive simply records abandonment nowhere else.
⛔ **And the rule the spec insisted on held: a plan with zero deliverables done is never treated as
`aborted`.** The 4 `indeterminate` plans are exactly where a lesser implementation would have guessed.

## Three bugs fixed along the way, and one is a PRQ-13 defect

1. ⛔ **`plan_rollup` reported `complete: true` over floor summands** (`7e09b2e`). A plan's `wall_seconds`
   can be `measured` with `floor: true`, and the roll-up ignored the flag — so a sum built from lower
   bounds was published as complete. ⭐ **This is a `PLAN-PRQ-13` defect, found by reusing its own
   pattern** — and it is the *floor-propagation* form of this epic's founding class: not a false zero, but
   a false *certainty*. Fixed: a floor summand now makes the sum incomplete.
2. **The severity roll-up silently dropped out-of-vocabulary values** — a measured value outside the band
   set was counted under an unemitted key and lost. Now `not_measured`.
3. **The engine's usage examples still showed it being run as a slash command** — a second front door
   surviving in the documentation after D6(a) closed the real one. Replaced, with a control that fails if
   one returns.

## Metrics and Anomalies

- **Tests: 924 passed, 20 skipped** (from 873 / 20), green before every commit. ⚠ **Reported by the run,
  not re-verified here**: the system `python3` has no pytest, and the run used plan-marshall's `.venv`
  interpreter. Recorded as the run's figure.
- No token figure, wall time, phase breakdown or landing-facts block — the lane's accepted cost, named
  before the run.
- 8 commits, no PR, no CI, no review bots; one deliberate self-review pass.

## Routing and Merge Behavior

- **Review:** none by design. The self-review pass found the three defects above, including the PRQ-13
  regression.
- **CI/merge:** no CI; suite green before each of the 8 commits; direct to `main`, pushed.
- **Collisions:** none possible — surface entirely out-of-repo, and nothing in `plan-marshall` or this
  ledger was touched, as the run states and the clean `plan-marshall` tree confirms.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `0adc341` — the head commit; there is no PR, by that repo's design
- [x] row `landing` stamped `landings/PLAN-PRQ-15.md`
- [x] row `plan_marshall_plan_id` left EMPTY — correct: no plan-marshall plan existed
- [x] `epic.md` narrative reconciled; WS-05 complete again
- [x] three Watches opened, one existing Watch sharpened

## Follow-Ups

**Three Watches:**

1. ⛔ **The `.adoc` output has never been rendered.** No AsciiDoc renderer is installed in that repository,
   so the aggregate's *markup* is unverified — the controls assert its content, not that it renders. ⚠ A
   human-readable report nobody has seen rendered is the one deliverable whose purpose is unconfirmed. —
   re-check by rendering it once.
2. ⛔ **Still nothing transferred, so no project report is committed — and this is now the SECOND plan to
   ship reports that have never run in anger.** PRQ-15 checked its work against a scratch copy of
   plan-marshall's real archive plus fixtures, which is materially better than fixtures alone, but the
   committed artefact does not exist. ⭐ **`transfer` + `analyze` for one project remains the highest-value
   action in this epic, and it needs no plan.**
3. ⚠ **The PRQ-13 tokens extractor writes `measured 0, floor: true`** when every per-phase `total_tokens`
   line is zero (example: `2026-09-17-plan-03-review-currency`). The aggregate renders it correctly as a
   floor, but a zero floor carries almost no information. Correctly scoped out of PRQ-15 as belonging to
   the tokens extractor. — fold into a future telemetry plan rather than leaving it to be rediscovered.

**One existing Watch sharpened:** the "reports shipped but never run against real data" Watch from
`PLAN-PRQ-13` now covers two plans' worth of unexercised output.
