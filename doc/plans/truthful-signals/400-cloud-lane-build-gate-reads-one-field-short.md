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

# The cloud lane's build gate reads one field short, and its report describes a build that ran as skipped

**Epic:** truthful-signals
**Branch prefix:** fix

⚠⚠ **THIS PLAN EDITS THE CONTRACT THAT GOVERNS THIS RUN.** The lane's own rule is that a run **never
self-approves a change to the contract that governs it.** ⛔ **Read that rule before Step 1 and follow
it**: where this plan's changes would need approving, the run **records the proposed change and says
so** rather than adopting it unilaterally. **The contract wins over this plan, and the disagreement is
reported.**

## Problem

Two of the lane contract's statements understate what they check, **in the same direction: toward
reporting clean.**

### Finding 1 — the build gate omits `errors[]`, at TWO sites

The repository-wide rule states it plainly: *after each build call, read the result `status` **and
`errors[]`** — the wrapper exits 0 even on failure.*

The lane contract requires `status` and `total_issues` and **never mentions `errors[]`** — in **both**
places it states the rule: the **per-commit** gate, and the **Step 5** build gate.

⚠ **Two sites, not one. A fix that corrects only Step 5 leaves the per-commit gate stating the weaker
rule — and the per-commit gate is the one that runs most often.**

⭐ **Why this is a false-green shape rather than a documentation nit: the lane's own sentence concedes the
premise** — *"the wrapper exits 0 on failure, so the exit code proves nothing; only the log does."* It
then names **two of the three** fields that make the log conclusive. **A build populating `errors[]`
while reporting a green status and zero issues satisfies the lane's stated check and is recorded as
clean.** The gate is one field short of the rule it is enforcing, **and the missing field is precisely
the one the repository-wide rule adds.**

### Finding 2 — the report records one of two build triggers

Step 5 defines **two** trigger surfaces deliberately, with an explicit callout noting that a
markdown-only change **can and does fail the build** — *it is how the contract's own first PR went red*:

| Changed | Run |
|---|---|
| Any `*.py` | the full verify |
| No `*.py`, but any skill or bundle source | the quality gate |
| Neither | record "no buildable footprint, build skipped" |

The run report's build-gate section asks for **only the first** — a Python-diff verdict, or *"no Python
changes, build skipped."*

⇒ **A run that changed no Python, correctly ran the quality gate, and passed it, reports the literal
sentence "no Python changes, build skipped."** **The report says no build ran when one ran and passed.**

⭐⭐ **The direction is what makes this serious: it is anti-correlated with the interesting case.** The
docs-and-skills-only change is **exactly** the run whose build coverage a reader would want to confirm,
and it is the run whose report is **guaranteed** to understate it. A reader auditing whether the skill
surface was linted **cannot tell a genuine skip from a passed quality gate**, and the report's own
vocabulary offers no way to express the difference.

⚠ **The two compound:** finding 1 weakens what *passed* means; finding 2 removes the record that a gate
ran at all.

## Goal

The lane's build gate checks every field the repository-wide rule names, and a run report can express
which of the three build outcomes actually occurred.

## Deliverables

1. **D0 — GATE: establish whether the wrapper can emit a green status with a non-empty `errors[]`.**
   Mutates nothing. Read the wrapper's result construction.
   *Done when:* the answer is recorded from source.
   ⛔ **This decides the plan's SEVERITY, not its wording** — and it is the claim the original reporter
   explicitly did **not** establish, flagging it as the discriminator. **If yes ⇒ finding 1 is a live
   false-green. If no ⇒ it is a defence-in-depth gap.**
   ⭐ **Either way the lane contradicts the repository-wide rule, so D1 proceeds regardless** — only the
   framing moves.
2. **D1 — Add `errors[]` to the gate at BOTH sites.**
   *Done when:* both the per-commit gate and the Step 5 gate name all three fields.
   ⛔ **Fixing one is the documented half-fix**, and the one most likely to be fixed is not the one that
   runs most often.
3. **D2 — Give the run report a vocabulary that distinguishes the three build outcomes**: the full verify
   ran, the quality gate ran, or there was genuinely no buildable footprint.
   *Done when:* a docs-and-skills-only run can report a **passed quality gate** rather than a skip.
   ⛔ **The current binary cannot express the middle case**, which is exactly why it collapses to the
   understating sentence.
4. **D3 — A check that the two trigger tables cannot drift apart.** Step 5 defines three rows; the report
   section asks for one. ⭐ **They are the same contract stated twice** — this epic's
   doc-contract-divergence archetype.
   *Done when:* one is derived from the other, or a check fails when they disagree.

**Four deliverables, one component.** ⛔ **Resist widening into the lane's other steps** — two findings
were routed here, not a lane audit.

## Out of scope

- **A general audit of the lane contract.** Two findings, scoped deliberately. Widening would put an
  unbounded review of the governing contract inside a run that contract governs.
- ⛔ **`doc/plans/**` — individual lane plans.** This plan changes the lane's **contract**, never a plan
  executed under it.
- **The merge gate's required-versus-decorative check distinction.** ✅ **Settled: a sibling cloud plan
  already owns it, derived from its own source spec.** ⇒ **Different gate, same file.** That one teaches
  the **merge** gate to tell a required status check from a decorative one; this one fixes the **build**
  gate's missing field and the report's wording. **No duplication.**

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — the per-commit gate, the Step 5 build gate, the Step 5
  trigger table, and the run-report build-gate section. **Located by quoted phrase, not by line.**
- The build wrapper's result construction — **read-only, for D0.** The exact module is named at D0.

⚠ **`.claude/skills/**` is a project-local surface** — a change here owes a plugin-cache sync, which a
cloud run cannot perform. ⛔ **Record that as owed in the run report.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The repository-wide rule requires reading `status` **and** `errors[]` | HYPOTHESIS | the repository guidance — **reachable and exact** |
| The lane contract names only `status` and `total_issues`, at two sites | HYPOTHESIS | the lane skill — **by quoted phrase.** ⚠ **The reported line numbers are the least durable part of the claim; the file has been edited since.** Re-verify by content |
| Step 5 defines three trigger rows with an explicit callout about markdown-only failures | HYPOTHESIS | the same file — ⭐ **the callout is the evidence that the middle row is deliberate** |
| The report section asks for only the Python-diff verdict | HYPOTHESIS | the same file, report section |
| The wrapper can emit a green status with non-empty `errors[]` | HYPOTHESIS | ⛔⛔ **NOT ESTABLISHED, and named as the gate. D0 settles it. Do not scope severity before it** |
| Any shipped run report actually mis-stated its build gate | HYPOTHESIS | ⛔ **NOT ESTABLISHED — only that the template REQUIRES the understating form.** ⇒ **Do not claim observed damage** |
| Twelve sibling findings on the originating PR are already fixed downstream | HYPOTHESIS | second-hand, and **not needed by any deliverable** — recorded only to explain why these two survived |
| No other staged plan owns this surface | HYPOTHESIS | ✅ **SETTLED: the adjacent cloud plan is a different gate.** ⛔ **But both edit the same file — serialize** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1 and D2 are text whose whole value is what a later RUN does with them, so both get a cold read.**
  Give the Step 6 verification sub-agent the amended gate text with no other context and a synthetic
  build result carrying a green status, zero issues, **and a non-empty `errors[]`** — then ask whether
  the gate passed. **The correct answer is NO.** If it passes, the wording is still one field short.
- **Second cold read for D2**: give it a run that changed no Python and passed the quality gate, and ask
  what the report should say. **The correct answer names the quality gate — not "build skipped."**
- ⛔ **D0's verdict must appear in the report either way.** "The wrapper can" and "the wrapper cannot" are
  both complete answers; only silence is a failure.
- **D3 must be verified by making the two tables disagree** and confirming the check fires.
- ⚠ **This run's own build gate is a live test of the thing being fixed.** Report which trigger fired and
  which fields were read — ⭐ **the plan is its own best fixture.**

## Notes

- ⭐ **Provenance worth keeping:** both findings surfaced as unresolved review threads on a PR that merged
  **through a lane with no thread-resolution step, so its threads stay open regardless of merit.** ⚠ **An
  open thread on that PR is not evidence of an unfixed defect** — most of its siblings were already
  fixed downstream. These two were **re-verified against the file as it stands**, which is why they are
  here and the others are not.
- ⛔ **Serialize against the sibling cloud plan that edits the same contract file.** Whichever runs second
  re-grounds against the other's landing. ⭐ **If that one runs first, re-check whether these findings are
  better carried through the same cloud path than as an ordinary local plan.**
- ⛔ **Do not go looking for the orchestrator spec, the routed inbox message, or any landing record.**
  They live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
