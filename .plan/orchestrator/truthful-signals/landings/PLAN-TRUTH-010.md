# Landing — PLAN-TRUTH-010 `fail-closed-signal-integrity`

**PR #1082** (MERGED 2026-08-02T21:47:23Z, squash `b713fe4b9`, branch `feature/fail-closed-signal-integrity`).
Whole-tree verify SUCCESS (17,361 passed). 8 commits, 29-file merged footprint.

## ⛔⛔ `ci pr merge` reported `merged: true` and deleted the branch WITHOUT merging

The landing message (21:09:09Z) states the plan *"shipped as **PR #1081**"*. First-party, `gh`:

| PR | State | Merged |
|---|---|---|
| **#1081** | **CLOSED** 2026-08-02T21:15:40Z | **never** — `mergedAt: null` |
| **#1082** | MERGED 21:47:23Z | `b713fe4b9` |

Identical title, identical head branch. ⇒ The real landing happened **38 minutes later** under a
different PR number.

⭐⭐ **The cause is NOT lateness — it is a lying oracle.** Per the operator's report: `ci pr merge`
returned **`merged: true`** and **deleted the branch** for #1081 **without merging it**. Recovery was a
re-push and #1082, enqueued with `ci pr merge-queue` — a verb that *honestly* returns `enqueued: true`.

⇒ **The landing message faithfully reported what the merge verb told it.** Caught only because the
author **re-derived `origin/main` instead of trusting the return value.**

⚠ **CORRECTION to this orchestrator's first reading of this landing.** I initially recorded the wrong
PR number as *"the strongest evidence yet for `PLAN-TRUTH-037`"* — a terminal report emitted before its
terminus. **That is largely wrong and I am striking it.** TRUTH-037's mechanism is *early emission*;
here the emission was correct **relative to the only signal available to it**. A remedy that moves the
message later would **not** have prevented this. ⭐ The residual TRUTH-037 signal is real but weak: a
later emission would have had a second chance to observe the truth. **The dominant defect is the merge
verb.** ⛔ *An explanation that fits the observation is not the same as the explanation that produced
it* — precisely this epic's discipline, and I skipped it for one revision.

⇒ **Routed to `review-apparatus`** (PR/CI-operation lane; the plan already filed it there, with its
provider-mapping hypothesis marked **explicitly unconfirmed**). This orchestrator's independent
corroboration — #1081 `mergedAt: null`, branch reused by #1082 — is forwarded with it.

⚠ The queue row is stamped **1082**, taken from PR state, **not** from the message.

## What shipped

| Arm | Delivered |
|---|---|
| D1 | `build-pyproject` file-to-build map routes `*.py.template` and non-Python test fixtures — a change to them can no longer map to "no build needed" |
| D2/D3 | `kind=build` change-ledger stamp gated on a build-executing-subcommand allow-list |
| D3 | New **Fail-Closed Classification** section in `ref-code-quality` — the standard the arms are graded against |
| D4b | `resolve_test_scope` fails closed on unmappable paths instead of returning an empty (benign) scope |
| D5 | Launch-abort pin (reduced to a stub-binary pin — see refutations) |
| + | Operator-directed: a derived-only `unknown` build status; an exit-0 payload carrying no recognised status can never derive `success` |

## Refuted arms — RESULTS, not gaps. ⛔ Do NOT re-queue.

1. **D4 (leaf record-before-return invariant) was ALREADY LANDED** in `agents.md`. Stale request arm.
2. **D4b's literal example (`.claude/skills/**`) was already fail-closed** — but the **CLASS was real**
   and confirmed at three other shapes. ⭐ **A wrong example does not refute the class**; dropping the
   arm would have discarded a live defect.
3. **The launch-abort arm was already fail-closed** (a negative returncode already maps to `killed`).

## ⛔ Yield: the plan found MORE fail-open defects in our machinery than it fixed

Seven independent instances of *could-not-measure rendered as measured-clean*, all first-party, all
found **while doing the work** — **three of them inside `phase-6-finalize` alone**:

| # | Site | The collapse |
|---|---|---|
| 002 | `manage-lessons restore-from-plan` | worktree-resident plan dir → `success / no_lesson_file` |
| 005 | `scope_creep_check` | `no_baseline_sha` alongside `residual_count: 0`, `finding_emitted: false` |
| 009 | `manage-lessons list-stalled` | `stalled_count: 0` while 8 `lesson-*.md` sat in the plan dir |
| 010 | `manage-status` `main_sha` invariant | records the **worktree** HEAD; drift warning describes a drift of `main` that never occurred |
| 011 | dispatch audit | `[DISPATCH]` under-counts ~35%; **zero** `resolve-target` records exist at all |
| 012 | `check-artifact-consistency` | `affected_files_recall: 0%` — true recall **100%** |
| 004 | `finalize-step-review-retrospective` | a **refused** reviewer and a clean one are both "no row" |

⭐ **The plan reproduced its own target defect seven times over in the machinery it used to ship the
fix.** That is the same self-implication PLAN-86 produced, and it is now the epic's most reliable
finding generator.

## ⭐⭐ Corpus impact — this landing CORROBORATES the token-measurement defect first-party

`metrics.md` published `total_tokens 2,782,409` with `> Partial: unrecorded phases — 6-finalize`.
`work/metrics-accumulator-6-finalize.toon`, **present on disk from the same subsystem**, already held
`total_tokens: 2,686,561` (16 samples, 612 tool_uses). Real spend ≈ **5,468,970**.

⇒ **The published figure is 51% of the truth.** And **6-finalize is the single largest phase — larger
than 5-execute by 2.2:1.**

### ⛔ THREE different totals for one plan, from three producers

| Source | Total |
|---|---|
| `metrics.md` (published artifact) | **2,782,409** |
| Retrospective reconstruction (published + the on-disk 6-finalize accumulator) | **≈5,468,970** |
| `record-metrics` step / operator report | **6.2M**, finalize 2.9M |

⭐ Note the third is **not** the second: `record-metrics` runs at finalize order 18, *after* the
retrospective, so it sees a phase row the retrospective could not. ⇒ **The producer's own number moves
depending on when you ask it**, and none of the three is labelled with which population it covers.
**That is `PLAN-TRUTH-035`'s thesis stated by the machinery itself**, and it widens 035: the defect is
not one artifact being partial, it is **three artifacts partitioning the same run differently with no
field saying so**. Folded into 035 as OBSERVED.

This is exactly the closed-phase-row / partiality defect recorded as *suspect* at the last drain, now
**OBSERVED**, and it settles two open questions in the same stroke:

- ✅ The **direction** I predicted was right — but I predicted `6-finalize`'s share was an
  **over-estimate**. ⛔ **Wrong sign.** Here 6-finalize is *dropped entirely*, so the corpus
  **under-**states it. ⇒ **The n=47 per-phase ranking is not merely imprecise, its error direction is
  not even uniform.** Do not repair it by adjustment; it must be re-derived.
- ✅ **The composition ratio still survives** — a dropped phase row omits all components together.
  "99% of cost is context" remains durable.

⇒ Folded into `PLAN-TRUTH-035` and into the roadmap caveat at the point of use.

## ⭐ Token-reduction datum: one finalize step cost 13% of the plan

`pre-submission-self-review`: **709,472 tokens**, 169 tool_uses, 39 min agent time, 5 passes, ~2h wall.
10 defects — **2 of them introduced by a prior pass of itself** ⇒ **89K tokens per externally-caused
defect**. One pass was killed by a harness stream stall and re-run, so part of the spend bought nothing.

⛔ And the defect that mattered most — a GOOD example demonstrating the anti-pattern its own clause
forbids, **in text this plan authored** — was missed by all five passes and caught by **CodeRabbit in
one pass at zero cost**. ⇒ A real, sized lever for the token-reduction roadmap, on measured numbers
rather than an estimate. See `roadmap-token-reduction.md` (L8).

## ⛔ MY OWN guard was never evaluated — orchestrator-side finding

The request carried a split guard: *"if the set runs past a reasonable size guard, split the launch-abort
arm and say so"*. The retrospective flagged that it was **never evaluated out loud**, and that **the set
unambiguously ran past it**.

⭐ That guard is the **scope-bloat guard, which is an orchestrator identity attribute** — a spec
approaching ~6 deliverables is presumptively split, and proceeding unsplit **requires a recorded
rationale**. I wrote the guard into the request as prose *conditional on the executor's judgement*
instead of deciding it at staging. ⇒ **A guard delegated to the party it constrains is not a guard.**
The plan ran 13h34m at 6.2M tokens across three loop-back rounds — the exact cost the guard exists to
bound.

**Standing correction, recorded here and in the anchor**: the scope-bloat decision is made **at staging,
by this orchestrator, with the rationale recorded before the command is emitted**. It is never phrased
as an instruction for the plan to self-assess.

## ✅ Correction accepted — pr-agent was NOT silent

I previously recorded that pr-agent reported *"no major issues"* on a diff where CodeRabbit found a
Major. **The review-retrospective checked the stored body: pr-agent flagged the `_module_for_path` root
mismatch that became finding `ba6d34` and a real fix.** ⇒ The claim is **withdrawn**; pr-agent
participated substantively.

⚠ **And note how the error was made** — from a *summary* of a review rather than from the stored
comment body. That is the standing rule *"only `ci pr comments` is evidence of participation"* violated
in the harder direction: not reading absence as refusal, but reading a **summary** as the review.
Recorded against the review-bot topic memory.

## Residue tracked

- **New specs staged**: `PLAN-TRUTH-044` (trapped-lesson corpus path, folding 002/003/009),
  `PLAN-TRUTH-045` (dispatch audit's empty evidence surface, 011), `PLAN-TRUTH-046` (`main_sha`
  records the wrong tree + `config_hash` cannot fail usefully, 010), `PLAN-TRUTH-047` (a retirement
  verdict justified by a self-contradicting example, 013 + the three owed trims from 015).
- **Routed to `review-apparatus`**: 004 (refused-vs-clean reviewer) — the PR/review test fires first.
- **Folded**: 005 → `PLAN-TRUTH-031`; 007/008 → archetype counters + `PLAN-TRUTH-012`;
  012 inst. 1 → `PLAN-TRUTH-037`; 012 inst. 2 + the metrics figures → `PLAN-TRUTH-035`;
  006/014 → `PLAN-TRUTH-014` and the roadmap.
- **OWED, operator-visible**: three lesson **trims** (`2026-07-16-14-001`, `2026-06-21-21-001`,
  `2026-07-22-12-003`) — each has a covered half to cut and an **uncovered half that must survive**.
  Deferred on cost at the end of a 13-hour run, not on judgement. Carried in `PLAN-TRUTH-047`.
- ✅ **Resolved during the run**: the 8 trapped lessons were restored (`restored_count: 8`) once
  `integrate_into_main` moved the plan dir back to main — which is itself the confirmation that 002's
  root cause is worktree-residency and nothing else.
- **Epic follow-up named by the plan**: enforce a single authoritative `_TEST_ROOTS` (remedy B, thread
  the root set through `resolve_test_scope`). ⛔ Size it against the consumer-sweep hazard — this run
  hit that hazard **twice** on that very signature.
