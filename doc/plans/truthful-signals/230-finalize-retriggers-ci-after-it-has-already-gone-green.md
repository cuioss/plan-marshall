> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Finalize spends what it need not — a second CI run per plan, and a self-review that cost 13% and saw nothing

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

**Finalize pushes commits AFTER the PR's CI has already passed**, forcing a second full CI run. Measured
over an archived corpus of 39 plans (36 with persisted CI records): **58 CI runs for 36 plans — a 61%
overhead**, with **16 plans (44%) running CI more than once**.

Two independent re-trigger sources, both addressable:

1. **Finalize's own source-mutating steps commit and push after PR creation.** The clearest case is the
   era-stamp fill, which by design resolves a pending sentinel to the **real PR number** and pushes the
   correction — which **cannot happen before the PR exists**, and therefore guarantees a post-green
   push. It ran in 27 of 39 archived plans.
2. **Triage loop-backs fire per producer.** CI verification, automated review, and the static-analysis
   round-trip are separate finding producers, each able to loop back independently; two plans recorded
   **three loop-backs**. Collecting findings across all producers behind **one** barrier turns N rounds
   into one commit and one CI run.

⭐ **The behaviour is already known and sanctioned** — the push standard names this exact class as
"finalize-internal re-stale (known-safe)" and the dispatcher carries a documented post-PR re-push fast
path. **What is missing is that nobody costed it.**

**And a second, independent way finalize spends without return:** the pre-submission self-review step
consumed **709,472 tokens — 13% of one plan's entire spend** — on a single step, and **still missed the
rule that fired**.

⭐⭐ **The sharpest datum available on that surface:** self-review passed **clean** over a
docstring-versus-code overclaim **in a plan whose whole subject was docstring-versus-code overclaims**.
The detector was blind to the exact defect class the plan existed to fix, on that plan's own diff. **A
clean self-review verdict is not evidence the class was checked.**

⇒ **And there is a mechanism for that blindness, which changes what the fix is.** Self-review findings
are **queried at the execute phase but filed at the finalize phase**, so absence is inferred from the
wrong phase. **"No findings" is structurally guaranteed rather than measured.** ⛔ **A zero from the
wrong phase is *could not look*, not *looked and found nothing*.** ⇒ **Fix the phase before scoping any
strengthening of the detector** — otherwise the plan spends effort making a blind detector sharper.

## Goal

A plan pays one CI run in the common case, one triage round rather than one per producer, and a
self-review whose clean verdict actually means the class was examined.

## Deliverables

1. **D0 — GATE: attribute the excess runs to their causes, and size the token side.** Mutates nothing.
   Split the excess between (a) post-green finalize-internal pushes, (b) triage loop-back commits, and
   (c) anything else.
   ⛔ **The corroborating evidence is a matched pair per plan**: two persisted CI manifests with the
   **same PR number and different head SHAs** is a genuine re-run. One confirmed instance shows a green
   run followed 59 minutes later by **another green run** on a new head.
   ⛔⛔ **BLOCKING CAVEAT FOR ANY COUNTING — do NOT count runs from work-log step markers.** Finalize
   step execution is **not uniformly logged**: across the corpus the step marker appears 33× for one
   step, 22× for another, 19× for another, and **1×** for another. **Absence of a marker does NOT mean
   the step did not run.** Any count from those markers is a **floor, not a measurement**, which is why
   attribution is pinned to the CI manifests.
   ⚠ **Also size the token side of the loop-back consolidation here**, so the benefit is measured rather
   than assumed — a plausible mechanism is not evidence.
   *Done when:* the attribution split is reported with its evidence per plan, and the token estimate is
   grounded.
2. **D1 — Stop the post-green push where it is avoidable.** For each finalize-internal source-mutating
   step that commits after PR creation, decide and record: can its mutation be computed **before** the
   PR exists, batched into the pre-PR commit, or deferred to the merge commit?
   *Done when:* every such step has a recorded verdict.
   ⛔ **The era-stamp fill is the hard case and must be reasoned about explicitly, not waved through.**
   It genuinely needs the real PR number, so it cannot run pre-PR. **The question is whether its
   correction must be pushed as its OWN commit, or can ride an existing one.**
   ⚠ It is meta-project-only, so this deliverable's benefit is ours, not our consumers'.
3. **D2 — One loop-back barrier across all finding producers.** Collect findings from every producer
   behind a single triage-and-loop-back decision, so one round of fix commits is produced instead of one
   per producer.
   *Done when:* two producers' findings in one finalize yield one loop-back round.
   ⛔ **This must not weaken fail-closed behaviour.** A batched barrier must still block the merge on
   **any** unresolved finding. **Batching is about *when* the loop-back fires, never about *whether* a
   finding gates.**
   ⚠ **Verify-first:** confirm the producers can share one barrier **without reordering the
   CI-completion precondition**. A barrier that forces CI-completion earlier would trade a CI re-run for
   a longer serial wait — a worse deal, silently.
4. **D3 — Fix the self-review phase mismatch BEFORE strengthening anything.** Make the findings query
   run in the phase where the findings actually exist.
   *Done when:* a self-review that examines nothing is **distinguishable from one that examined and
   found nothing**.
   ⛔ **This is the prerequisite for every other self-review improvement.** Strengthening a detector
   whose query runs against the wrong phase adds cost and changes nothing.
5. **D4 — Scope the self-review to what it can usefully check.** Given D3, decide what the step should
   examine for its cost.
   *Done when:* the step's scope is recorded with its expected cost, and the report states the absolute
   token figure it is measured against.
   ⛔ **The ratio claims from the source measurement remain blocked behind D0; the absolute numbers are
   solid.** Report absolutes; do not publish a ratio the measurement cannot support.
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) A plan whose only post-PR mutation is the era-stamp produces **ONE** CI run, not two.
   - (b) Findings from two different producers in one finalize produce **ONE** loop-back round.
   - (c) **Fail-closed still holds**: an unresolved finding from any single producer still prevents merge
     under the batched barrier.
   - (d) A self-review over a diff containing a known-detectable defect **finds it** — the test that
     distinguishes a working detector from a phase-mismatched one.
   *Done when:* all four pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables. The source spec, after absorbing
a second plan, stood at **ten against a raised cap of twelve** — and its own note warned that
**overlapping deliverables should COLLAPSE rather than concatenate**, and that a merged plan still
reading as two plans stapled together has not been merged. **That collapse is applied here.** The two
halves share a component, a measurement substrate, and the re-measurement work — which is the expensive
part and would otherwise be done twice. ⚠ **Re-count at outline**; if D3–D4 prove separable from D0–D2
in practice, say so and ship the CI half first.

## Out of scope

- ⛔ **Moving the rebase later in finalize. DO NOT RESURRECT THIS.** A predecessor plan proposed it and
  the same measurement **refuted the premise**. The early rebase is a conflict **pre-filter** that keeps
  conflict resolution **outside the merge mutex**; moving it later is counter-indicated.
- **Redesigning the self-review detector set.** D3 fixes the phase; D4 scopes the step. **Making the
  detectors smarter is deferred until a clean verdict means something** — otherwise the improvement
  cannot be measured.
- ⛔ **The self-review SURFACING layer.** Owned by
  `doc/plans/code-intelligence-substrate/100-self-review-surfacing-integrity.md`: a detector reading a
  narrower file set than its own sibling, registry entries counted as examined by nothing, and a scoped
  round making whole-surface claims. ⭐ **Adjacent but genuinely disjoint** — that plan owns *which files
  and detectors get surfaced*; this one owns *when the findings query runs and what the step costs*.
  ⛔ **Do not run them concurrently** (same step, same bundle), and ⭐ **prefer this plan FIRST**: while
  the query runs against the wrong phase, that plan's coverage improvements cannot be measured.
- **Consumer-facing changes from D1.** The era-stamp step is meta-project-only. Do not generalise its
  fix into shared surface on the strength of a meta-project measurement.

## Expected surface

- `.claude/skills/finalize-step-era-stamp-fill/**` — project-local, meta-project-only.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the dispatcher's commit
  instrumentation and the post-PR re-push fast path.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md`,
  `.../workflow/sonar-roundtrip.md`, and the automated-review skill — the D2 barrier.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — already documents the
  finalize-internal re-stale class.
- The pre-submission self-review surface and its findings query (D3, D4).
- `test/plan-marshall/phase-6-finalize/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 58 CI runs across 36 plans with persisted records; 16 re-ran; distribution 20×1, 11×2, 4×3, 1×4 | OBSERVED | the archived CI manifests. ⛔ **Not reachable from this clone** — the corpus is under `.plan/`. Treat the figures as the **motivation**, and have D0 re-derive from whatever corpus is available |
| A genuine re-run pair exists: same PR number, two head SHAs, 59 minutes apart, **both green** | OBSERVED | those two manifests — same caveat. ⭐ Green-then-commit-then-green is a **real observed pattern**, which is the plan's premise |
| The era-stamp step ran in 27 of 39 archived plans | OBSERVED | the corpus — a **lead**, not reachable here |
| The push standard already names the finalize-internal re-stale class, and a post-PR re-push fast path is documented | OBSERVED | `push.md` and the finalize SKILL.md — **both reachable from this clone; verify these directly** |
| Finalize step execution is not uniformly logged (33 / 22 / 19 / 1 markers for four steps) | OBSERVED | the corpus. ⛔⛔ **The load-bearing caveat**: any marker-derived count is a **floor**, not a measurement |
| All 16 multi-run plans also recorded a loop-back; no plan had >1 CI run with zero loop-backs | OBSERVED | the corpus — a **lead** |
| The excess is dominated by post-green pushes rather than by loop-backs | HYPOTHESIS | **D0.** The confirmed pair is **one instance, not a distribution.** ⚠ Both causes are real; **the split is unmeasured** |
| Consolidating loop-backs yields a material token saving | HYPOTHESIS | **D0.** ⛔ Raised as a likely benefit; **a plausible mechanism is not evidence** |
| Self-review cost 709,472 tokens — 13% of a plan's spend | HYPOTHESIS | ⛔ **the absolute figure is reported solid; the RATIO is blocked behind D0.** Report the absolute |
| Self-review passed clean over the exact defect class its own plan was fixing | HYPOTHESIS | that plan's diff and its self-review record — ⛔ under `.plan/`, **not reachable here**. Reproduce the shape instead: D5(d) is that test |
| The findings query runs at the execute phase while findings are filed at finalize | HYPOTHESIS | the self-review query path and the findings writer — **by symbol. ⛔ This is D3's whole premise and the most checkable claim in the plan** |
| The producers can share one barrier without reordering the CI-completion precondition | HYPOTHESIS | the dispatcher's precondition resolution — **verify before scoping D2** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(d) is the test that matters most.** A self-review must be shown to **find** a defect it should
  find. Every other self-review test can pass on a detector that examines nothing.
- ⛔ **D5(c), the fail-closed case, is the safety test for D2.** A barrier that batches findings and
  loses one is strictly worse than N barriers.
- **D0's attribution must state the population and the evidence per plan.** A split between causes with
  no per-plan evidence is an opinion with numbers attached.
- ⛔ **Do not report any figure derived from the step markers without labelling it a floor.** That
  caveat is the single most reusable thing in this plan.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing:** a sibling plan owns **gate re-firing over the loop-back diff** and holds the same
  finalize surface. **Sequence after it lands and re-ground D2 against whatever it changed.** Another
  sibling adds **structured finalize step records** — that is the observability prerequisite that makes
  D0's attribution *re-derivable later*. This plan can proceed on the CI manifests alone, but **prefer
  the records plan first if both are queued**.
- ⛔ **Do not go looking for the orchestrator spec, the archived corpus, the drained messages, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. Where a
  figure came from that corpus, this file says so and marks it a lead.
