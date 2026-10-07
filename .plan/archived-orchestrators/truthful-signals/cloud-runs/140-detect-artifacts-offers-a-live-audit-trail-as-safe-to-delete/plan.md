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

# `detect-artifacts` offers a running plan's own live audit trail as safe-to-delete

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`detect-artifacts` in `workflow-integration-git` is **documented as excluding gitignored files** from
its safe-to-delete classification. Reportedly it does not. On one observed run it returned **111,433
"safe-to-delete" entries totalling 19.9 MB** — including the running plan's **own in-flight
`work.log`**, and the entire `.mypy_cache/` tree. Both gitignored. Both live at scan time.

A caller that follows the documented instruction *"for safe artifacts, delete them"* therefore
destroys the audit trail of the run that is still producing it.

⛔ **The failure mode is silent destruction of evidence.** The damage is invisible when it happens and
surfaces later only as degraded measurement — because `work.log` is exactly the artifact the dispatch
audit and the retrospective read. Nothing trips at the moment of loss.

⚠ **EVERY OBSERVATION ABOVE IS SECOND-HAND.** It reached this plan as a forwarded lead from another
epic's run, and **nobody has independently re-read `detect-artifacts`**. That is why D1 is a gate: the
plan re-establishes the defect at HEAD before anything is changed, and is willing to conclude it does
not exist.

## Goal

No classification offered as safe-to-delete can contain a live artifact of a running plan — and the
documented contract and the implementation agree about gitignored paths, in whichever direction is
chosen.

## Deliverables

1. **D1 — GATE: re-establish the defect at HEAD, and derive the exposure.** Mutates nothing.
   Confirm the gitignore-exclusion contract is stated where it is claimed to be, and confirm the
   classification ignores it. Then enumerate **what a compliant caller would actually delete today**.
   *Done when:* the contract text and the classification behaviour are both quoted from source, and
   the exposure set is derived with its method stated.
   ⛔ **STOP CONDITION — this deliverable may end the plan.** If the contract does not say what it is
   claimed to say, or the classification already honours it, **halt and report the lead as refuted**.
   Do not manufacture a fix for a defect that is not there.
   ⛔ **Do not fix before the exposure is derived.** The `work.log` case is a **SAMPLE**. The
   interesting question is *what else* is live-and-gitignored — lock files, in-flight findings, the
   change ledger, worktree state. **The 111,433 figure is one run's number, not the contract's blast
   radius.**
2. **D2 — Decide the direction, and record why.** Exactly one of:
   - **(a) Honour the documented contract** — genuinely exclude gitignored paths; or
   - **(b) Narrow the documentation to actual behaviour AND add a liveness/staleness check** —
     mtime-based or lock-aware — before any gitignored path is offered as safe-to-delete, especially
     anything under an **active plan's own `logs/`**.
   *Done when:* one direction is chosen and its rationale recorded.
   ⛔ **(b) without the liveness check is NOT acceptable.** That would *document* the data-loss path
   instead of closing it, which is this epic's archetype committed deliberately.
3. **D3 — An active plan's own artifacts are never offered.** Whichever direction D2 takes, a path
   belonging to a currently-running plan **must not** appear in a safe-to-delete set.
   *Done when:* the invariant holds and is pinned by a test.
   ⭐ **This is the real invariant, and it is independent of the gitignore question.** Even a
   correctly-classified, non-gitignored artifact of a live run should not be offered for deletion by
   that run's own finalize. If D1 refutes the gitignore claim, **D3 still stands on its own** and the
   plan ships it alone.
4. **D4 — Find the callers.** Establish whether any caller acts on the classification **automatically**
   today, and how close this came to firing.
   *Done when:* the caller set is derived — not sampled — and the report states whether the defect is
   latent or active.
   ⛔ **Derive it; do not assume the optimistic case.** A documented instruction with no automatic
   caller is a *latent* defect; one with an automatic caller is an *active* one, and **the severity of
   D2 and D3 depends on this answer**.
5. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) A gitignored path is excluded per the contract — or, under D2(b), excluded by the liveness
     check.
   - (b) **A live plan's own `logs/work.log` is never in the safe-to-delete set.**
   - (c) D1's exposure derivation is asserted **non-empty and contains a known member** — the
     positive-population assertion, without which a scan that matched nothing looks identical to a
     clean tree.
   *Done when:* all three hold and the report states each was seen red first.

Five deliverables, under the split presumption.

## Out of scope

- **A general artifact-retention policy.** This plan stops a specific destructive classification; it
  does not decide how long artifacts should live or who prunes them. Widening into retention design
  would put an unreviewed deletion policy under every plan, which is the opposite of the goal.
- **The worktree teardown timeout.** A hardcoded ceiling on `worktree-remove` is a known adjacent
  defect on the **same teardown surface in the same bundle**. ⭐ **Consider folding it in at outline
  only if D1's derived surface actually reaches it** — otherwise leave it, because a timeout defect and
  a data-loss defect share a file but not a mechanism.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/**` — `detect-artifacts`, its
  contract documentation, and the classification implementation. ⛔ **This is the whole premise and it
  is unverified** — establish every location **by symbol** at D1.
- Callers surfaced by D4 — unknown at authoring time.
- `test/plan-marshall/workflow-integration-git/**`.

⚠ **No line numbers are asserted anywhere in this plan, deliberately**, because its evidence is
second-hand. Anchoring on a line number here would give inherited hearsay the appearance of a checked
location.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `detect-artifacts` is documented as excluding gitignored files | HYPOTHESIS | the `detect-artifacts` contract text in `workflow-integration-git` — **D1 owns this, and it is the whole premise** |
| The classification does **not** honour that exclusion | HYPOTHESIS | the classification implementation, read by symbol |
| One run classified 111,433 entries / 19.9 MB as safe-to-delete | HYPOTHESIS | ⛔ **forwarded from another epic's run and NOT independently verified.** Not reproducible from this clone. Treat as motivation; **D1 derives the real exposure** |
| That set included a live plan's own `work.log` and the `.mypy_cache/` tree, both gitignored | HYPOTHESIS | same provenance caveat. Reproducible in principle by running the classification in a tree with a live plan |
| No caller deletes automatically today | HYPOTHESIS | **D4. ⛔ Do not assume it** — this is an asserted **absence**, the higher-risk half, and it is the difference between a latent and an active defect |
| A plan's own artifacts are identifiable as belonging to a *running* plan at classification time | HYPOTHESIS | whatever liveness signal exists — a lock, a status record, an mtime. ⛔ If **no** such signal is reachable, D3 cannot be implemented as stated and the run must say so rather than approximating it |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(b) is the deliverable that matters.** Everything else is supporting work: the plan exists so
  that a run's finalize cannot offer that run's own audit trail for deletion. If only one test survives
  review, it is this one.
- ⛔ **D5(c)'s positive-population assertion is not optional.** An exposure derivation that returns
  nothing looks exactly like a clean tree, and this epic's namesake defect is a check that passes
  because it examined nothing.
- **D4's caller set must be derived from the population, with the query stated** — a list of call sites
  produced by looking is a **sample, not an enumeration**, and this project has shipped a wrong
  "N consumers updated" claim on exactly that mistake more than once.
- If D2 chooses (b), the report must show the **liveness check firing**, not merely that the
  documentation was narrowed. Narrowed docs without the check is the explicitly rejected outcome.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing:** two other plans touch the branch-cleanup document, which is adjacent to
  worktree and artifact teardown. **Verify before pairing.** Otherwise this is disjoint from the usual
  in-flight surfaces.
- ⭐ **The routing rationale, recorded because it is a useful precedent:** the damage lands in another
  epic's measurement substrate, but *a documented contract the implementation does not honour* is a
  behaviour/contract signal — so the fix belongs where the contract lives, not where the symptom was
  felt.
- ⛔ **Do not go looking for the orchestrator spec, the forwarded inbox message, the originating plan's
  self-review finding, or any landing record.** They live under `.plan/`, which is git-ignored and
  absent from this clone. Everything needed is in this file — and where the evidence is genuinely
  second-hand, this file says so rather than dressing it up.
