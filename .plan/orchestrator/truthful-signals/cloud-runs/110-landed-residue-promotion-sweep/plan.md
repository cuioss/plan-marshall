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

# Landed-residue promotion sweep

**Epic:** truthful-signals
**Branch prefix:** chore

## Problem

A lesson records a specific defect and its fix. When the fix ships, the *specific* half is discharged
— but the **generalizable rule** underneath it often was never written into the standards of the skill
that owns the surface. The lesson is then retired or ages out, and the rule leaves with it. The next
author inherits nothing.

The sweep exists to promote each such residue into its governing skill's standards, cross-linking the
shipped fix as a worked example, so the rule outlives the lesson that discovered it.

⛔ **READ THIS BEFORE SCOPING ANYTHING — the plan's input set is not reachable from this clone, and
may no longer exist at all.** The residue set was bound as a list of ~24 lesson identifiers in a
`manage-lessons` store. That store lives under `.plan/`, which is **git-ignored and absent from this
clone**, so the identifiers cannot be resolved here. Worse: a check on the authoring machine found the
live corpus holds **23 active lessons, none of them from the dated range this plan carries** — the
carried set appears to have been retired or aged out since the plan was staged.

⇒ **This plan is therefore mostly a derivation problem, not a writing problem**, and D0 exists to
settle whether it is executable at all before any standards file is touched.

## Goal

Every promotable residue that can be **established from git-reachable evidence** is written into the
standards of the skill that owns its surface, as durable guidance a future author inherits — and
anything that cannot be so established is reported as unexecutable rather than reconstructed from
memory.

## Deliverables

1. **D0 — GATE: establish whether the residue set is derivable at all.** Mutates nothing.
   Attempt to reconstruct the promotable residue set from **git-reachable evidence only** — merged
   PRs, commit messages, and the standards files themselves.
   *Done when:* the run reports either a derived residue set with the method that produced it, or a
   statement that it is not derivable.
   ⛔ **STOP CONDITION — THIS DELIVERABLE MAY END MOST OF THE PLAN.** If the residue set cannot be
   derived from git, **halt D2 and report that**, then ship D1 alone (which is self-sufficient — see
   below).
   ⛔ **Do NOT reconstruct a lesson's content from its identifier, from this plan's prose, or from
   inference about what a dated id probably meant.** A promoted "rule" that nobody actually learned is
   worse than a missing one: it enters the standards with the authority of experience and none of the
   evidence. **An unresolvable identifier is dropped and reported, never guessed.**
2. **D1 — Promote the three build/`script-shared` residues restated in full below.** These are the
   only residues whose content is carried in this plan rather than referenced by id, so they are the
   only ones executable regardless of D0's verdict.
   *Done when:* all three are written into the governing standards with the stated caveats intact.
   ⛔ **Label all three as run-observation when promoting** — they were established by watching a run,
   **not** derived from the shipped diff, and the standards entry must say so.

   **(a) The buffering property that makes the obvious diagnostic vacuous.** The build wrapper's
   output is buffered until completion, so while a job runs the output file is empty — and after a
   kill it is *also* empty. **The two states are byte-identical.** An empty background-job output file
   is not evidence of "still running" and not evidence of "killed"; it carries **no information at
   all**, and polling it is reasoning from a constant.

   **(b) The change-ledger is the substitute oracle.** A build that actually ran appends a
   `kind=build` row stamped with the `worktree_sha`; no row means the build did not complete, whatever
   the output file looks like. This is the same substrate the execute phase reads for its freshness
   assertion.
   ⚠ **Promote this WITH its caveat, never without it.** `kind=build` rows are currently
   **over-inclusive** — a `--help` invocation and a pure log read both stamp one — so the ledger is
   the *best available* oracle, **not yet a sound one**. Promoting it as unconditionally authoritative
   would manufacture a fresh **vacuous-authority** instance, which is this epic's most-repeated
   archetype.

   **(c) The mitigation that actually worked.** Foreground invocation plus an explicit Bash timeout of
   600000 ms, letting the harness auto-background at its own ceiling. The observed asymmetry is the
   point: **harness-initiated auto-backgrounding preserved the job every time; caller-initiated
   background execution was killed twice on the same long build**, producing zero output and no ledger
   row.
3. **D2 — Promote whatever D0 derived.** For each derived residue: confirm the fix is in current
   source **and** that the rule is **not already** in the governing standard; promote it; cross-link
   the shipped fix as a worked example.
   *Done when:* each derived residue is promoted, or recorded as already-covered and dropped.
   ⛔ **An already-covered residue is dropped, not re-stated.** Adding a second copy of an existing
   rule is the duplication defect this project already tracks.
   ⚠ If D0 yields a large set, **batch by governing skill and ship the batches serially** rather than
   inflating one PR across fifteen skills. Report what was deferred.
4. **D3 — Parity tests only, where a promoted rule has a mechanical form.** No behaviour change.
   *Done when:* any test added asserts the rule and nothing else; if no promoted rule has a mechanical
   form, this deliverable is explicitly reported as empty rather than padded.

⭐ **Split-guard verdict, recorded before hand-over:** the source spec was carrying **twelve**
deliverables at a raised cap of twelve, most of them batches of by-identifier residues. **This plan
deliberately does not carry that count forward**, because D0's stop condition makes almost all of it
conditional — writing twelve deliverables against an input set that may be empty would be a plan whose
size is fiction. The real shape is: one gate, one self-sufficient promotion, one conditional
promotion, one conditional test. **If D0 succeeds and yields a large set, re-batch and say so.**

## Out of scope

- **Any production behaviour change.** This is a standards-and-guidance sweep. A promoted rule that
  requires code to change is **recorded as a follow-up**, not implemented here — the plan has no
  review budget for behaviour it did not declare.
- **Reviving retired lessons.** If the carried identifiers turn out to have been retired deliberately,
  that is a decision already taken by someone with more context than this run has. Report it; do not
  reverse it.
- **The absorbed producerless-`phase-1-init`-posture item.** A second plan was merged into this one on
  the strength of a shared *component*, not a shared mechanism, and that merge was recorded as **the
  weakest in its set**. ⛔ **It is excluded here.** Its subject — a compose-side field with two readers
  and no producer — is a genuine defect and belongs with the producerless-contract-row work in this
  epic, not inside a documentation sweep. Folding it in would produce a plan that reads as two plans
  stapled together, which the merge itself explicitly permitted undoing.

## Expected surface

Standards documents under `marketplace/bundles/`, in the skills that own each promoted rule. The
candidates named by the source spec — **all unconfirmed until D0 derives the actual set** —
were `build-pyproject`, `script-shared`, `manage-config`, `manage-execution-manifest`,
`tools-script-executor`, `manage-status`, `automatic-review`, `marshall-orchestrator`,
`workflow-integration-git`, `workflow-integration-github`, `manage-providers`, `phase-1-init`,
`manage-plan-documents`, `persona-module-tester`, and `pm-dev-python:pytest-testing`.

**D1's three residues land in the build / `script-shared` standards specifically.**

⚠ **Wide but shallow, and docs-only.** Collision risk is broad, so this plan is **low-priority and
best run when little else is in flight**.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat every claim below as `HYPOTHESIS` unless marked otherwise**, including every count and every
file list. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The carried lesson identifiers are **not resolvable from this clone** | OBSERVED | the `manage-lessons` store lives under `.plan/`, which is git-ignored — confirm by observing that no such directory exists here. This is an asserted **absence** and it is **load-bearing**: it is what makes D0 a gate rather than a formality |
| The live corpus on the authoring machine contained **none** of the carried dated identifiers | HYPOTHESIS | ⛔ **not verifiable from this clone at all.** Recorded because it materially changes the plan's odds, not because the run can check it. Do **not** treat it as licence to skip D0 |
| The three D1 residues are accurate as stated | HYPOTHESIS | (a) the build wrapper's buffering behaviour — reproduce by starting a long build and reading the output file mid-run; (b) the `kind=build` row and its `worktree_sha` stamp — read the change-ledger writer; (c) the timeout mitigation — the asymmetry is a **run observation** and may not be reproducible on demand |
| `kind=build` rows are over-inclusive (a `--help` call and a log read both stamp one) | HYPOTHESIS | the ledger-writing call sites. ⛔ **This caveat is mandatory in D1(b)'s promotion** — verify it, and if it has since been fixed, say so and promote the corrected form |
| For each residue, the rule is not already in the governing standard | HYPOTHESIS | each governing standard, per residue. ⛔ An asserted **absence**, and the one most likely to produce duplicate work |
| Every carried residue's fix is already in current source | HYPOTHESIS | git history per residue — the premise that makes this a promotion sweep rather than a fix sweep |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **Every promoted rule is text whose entire value is what a later author does with it**, so the
  promotions get a **cold read**. Give the Step 6 verification sub-agent one promoted rule with no
  other context, plus a short code or process sample that violates it, and ask whether the sample is
  acceptable. The correct answer is **no**. A rule the cold reader cannot apply has been filed, not
  promoted.
- **D1(b)'s caveat must survive the cold read specifically.** Ask the reader: *"is a missing
  `kind=build` row proof the build did not run?"* The correct answer is **yes**, and *"is a present
  row proof it did?"* — the correct answer is **no, the row is over-inclusive**. If the reader reads
  the ledger as unconditionally authoritative, the caveat was dropped or buried and the promotion has
  created the vacuous-authority instance it was warned about.
- **D0's report must state its derivation method and its population**, not just its output. "I found N
  residues" without saying how is the volume-read-as-coverage archetype.
- Docs-only is expected, so the build gate will likely take its docs-only path. **Confirm from git
  evidence rather than assuming** — D3 may add tests, which changes that.

## Notes

- ⚠ **This plan is a strong candidate for being superseded rather than executed.** If D0 establishes
  that the residue set is gone, the honest outcome is a run that ships D1's three residues, reports
  the rest as underivable, and **recommends the plan be closed** — not one that manufactures twenty
  plausible-sounding rules. Recommending closure is a legitimate result here.
- ⛔ **Do not go looking for the lessons store, the orchestrator spec, the absorbed spec, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. What is
  needed and knowable is in this file; what is missing is missing, and saying so is the deliverable.
