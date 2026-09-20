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

# A finalize step acts on a file set that is not the file set it actually touched

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Two ends of one defect.

**End one — the footprint a guard is allowed to SEE.** The post-run source guard exists to catch tracked
source that a finalize step left dirty with no push path. It filters out **everything under `.plan/`**,
on the assumption that `.plan/` is plan state and therefore never tracked.

**That assumption is false.** A number of files under `.plan/` **are git-tracked**, including the
project configuration and every architecture descriptor. The guard therefore reports `clean: true` over
**precisely the paths where an unpushable tracked edit is most likely** — the architecture-enrich writes
that happen at the end of finalize.

⛔ **The filter runs AFTER the porcelain observation has already restricted to tracked paths**, so
**every path it drops is known-tracked.** ⭐ **This is the same defect class re-entering through the
guard built to close it.**

**End two — the footprint a step is TOLD about.** The declared affected-file list is **frozen at outline
time**, so any scope movement during execution is lost, and **every derived finalize gate under-scopes**.

⭐ **Why these must ship together:** fixing the guard while the declared footprint stays narrow just
**moves the blind spot** — the guard now sees correctly and is handed a wrong list. Both are *"the set
of files this step believes it is responsible for"*, and they share consumers.

## ⭐⭐ It is NOT one site, and an earlier scoping said it was

A sweep found **six non-test production files carrying a literal `.plan/` path exemption**:

| Site | Status |
|---|---|
| the post-run source guard | ⛔ **CONFIRMED same defect** |
| the plan invariants module's main-dirty filter | ⛔ **CONFIRMED same defect** — drops every `.plan/`-prefixed path on the same "normal bookkeeping" rationale |
| a path-attribution merge helper | ⚠ **UNCLASSIFIED — check at D0** |
| a manifest-consistency check | ⚠ **UNCLASSIFIED — check at D0** |
| a routing-decisions check | ⚠ **UNCLASSIFIED — check at D0** |
| the gitignore setup script | ✅ **EXPECTED — not a defect.** Its job *is* `.plan/` gitignoring. **The matched negative control.** |

⭐ **The two confirmed sites fail identically and independently**: each drops a path on a **prefix**
rather than on a **property of the file**, so each is blind to the same tracked files. **A fix to one
leaves the other live.** ⛔ **This is why the fix must be a shared predicate, not an edit to one
function** — otherwise the plan fixes the guard that was noticed and leaves the invariant that was not.

⚠ **The three unclassified rows are a FLOOR, not a verdict.** They were found by a literal-string sweep
and have not been read. **A count of six with three unexamined is exactly the volume-read-as-coverage
failure this epic tracks.**

## Goal

Every guard's exemption depends on **trackedness rather than on a path prefix**, every clean verdict
carries the population it examined, the declared affected-file list reflects scope as it moves, and a
finalize step that legitimately produces a tracked write has a stated push path.

## Deliverables

1. **D0 — GATE: classify the whole exemption population.** Mutates nothing.
   *Done when:* **every site is classified as same-defect / different-purpose / negative-control, and the
   classification is published** with the population it was derived from.
   ⛔ **Also re-derive the tracked-file set under `.plan/` against HEAD.** ⚠ **If that set is empty, the
   premise is REFUTED and the plan re-scopes** — the defect is only live while tracked files exist there.
2. **D1 — Replace the prefix exemption with a trackedness predicate, as a SHARED predicate.** A `.plan/`
   path is exempt **only when it is NOT git-tracked**; a tracked `.plan/` file is reported like any other
   tracked source.
   *Done when:* **every D0-confirmed site uses one predicate**, not a per-site copy.
   ⛔ **Stated as a shared predicate, not as an edit to one function.** Two copies of a rule is how the
   second site stayed live after the first was noticed.
3. **D2 — Publish the examined population.** Each guard's own output states paths considered, paths
   exempted, and why.
   *Done when:* a `clean: true` is **distinguishable from a looked-at-nothing pass**.
   ⭐ This is the epic's standing rule — **a zero must carry its population** — applied to the guard
   itself.
4. **D3 — Fix the declared footprint at its FREEZE POINT, not at its consumers.** The affected-file list
   must be updated when scope moves during execution — **or every consumer must be taught it is a
   *declaration*, never a *record*.**
   *Done when:* one of those two is implemented, and the choice is recorded.
   ⛔ **Patching each derived gate to re-derive its own scope would multiply the source of truth.**
   ⛔ **Approval is not recording.** One confirmed instance was a **legitimate** widening of over 700
   lines that still never reached the manifest — so **a fix keyed on "unsanctioned scope" would miss the
   confirmed instance.**
   ⛔ **The absorbed premise was REFUTED as originally stated**: the field is *present* on the large
   majority of records. The defect is **inconsistent writing and under-recording**, not absence. **Do not
   implement the absent-key remedy** — it fixes a small fraction and leaves the silent half.
5. **D4 — Decide and document the disposition for a legitimately-dirty tracked `.plan/` file at
   finalize.**
   *Done when:* a stated remedy exists — **not merely a surfaced problem.**
   ⭐ **The recurring instance is an enrich write the run KNEW it owed** — so the question is not *"what
   do we do with an unexpected dirty file"* but *"a finalize step legitimately produces a tracked write
   and there is no push path for it."* ⛔ **D4 must ANSWER that**, or the fixed guard converts a silent
   hole into **a recurring block on every plan that enriches.**
   ⚠ **If answering it requires a decision this run cannot make, RECORD A PROPOSAL** with the options and
   their consequences, and say so.
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) **A positive control**: a dirty **tracked** `.plan/` file **IS** reported. ⛔ **The guard must be
     seen to fail against this today.**
   - (b) **A matched negative control**: a dirty **untracked** `.plan/` file is **NOT** reported.
   - (c) The same pair against **every** D0-confirmed site, not only the first.
   - (d) The published population is asserted non-empty.
   *Done when:* all four pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables. The source spec, after absorbing
a sibling, was counted at **eight against a raised cap of twelve**, with its own instruction that
overlapping deliverables **COLLAPSE rather than concatenate.** That collapse is applied.

## Out of scope

- **Changing what architecture-enrich writes, or when.** This plan changes only **whether the guard can
  see it**, and (via D4) what happens when it does. Changing the writer is a different surface with
  different reviewers.
- **Re-deriving scope inside each consumer gate.** ⛔ Explicitly rejected in D3 — it multiplies the source
  of truth, which is the failure mode one level up.
- **The gitignore setup script's `.plan/` handling.** ✅ **Correct by construction — it is the negative
  control**, and "fixing" it would break the thing that makes `.plan/` ignorable at all.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` — the
  prefix constant and the two filter functions, **by symbol**.
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — the main-dirty path
  filter, **by symbol**.
- The three unclassified sites — `extension-api`'s path-attribution merge helper, and two
  `plan-retrospective` checks — **read at D0 before touching**.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the contract prose that restates
  the guard's behaviour.
- The affected-file freeze point (D3).
- `test/plan-marshall/phase-6-finalize/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The guard filters on a bare path prefix, unconditionally | OBSERVED | that file § the prefix constant and the filter — **by symbol** |
| The filter runs AFTER the observation has restricted to tracked paths, so every dropped path is known-tracked | OBSERVED | the same file § the checking function. ⛔ **This is what makes it a defect rather than an over-approximation** |
| Files under `.plan/` are git-tracked, including the config and the architecture descriptors | HYPOTHESIS | ⛔ **re-derive with a tracked-file listing at HEAD.** ⚠ **If the set is EMPTY the premise is refuted** — this is the plan's verify-first clause |
| A second site implements the same prefix filter | HYPOTHESIS | the invariants module, **by symbol** — ⛔ **the reason D1 must be a shared predicate** |
| The three unclassified sites | HYPOTHESIS | ⛔ **found by a literal-string sweep and NOT read.** A floor, not a verdict — **D0 classifies and publishes** |
| The live instance: architecture descriptors dirty on main after a finalize, with the guard reporting clean | HYPOTHESIS | ⛔ **a machine state under `.plan/`, not reachable from this clone.** ⚠ **Reported LIVE at staging time with an open operator decision** — treat as motivation, and note it may since have been resolved |
| The guard's docstring rationale is the origin of the assumption | HYPOTHESIS | that module's docstring — ⭐ **and the right place to correct the contract** |
| No second consumer re-implements the prefix filter beyond those found | HYPOTHESIS | ⛔ asserted **absence** — the sweep is the evidence, and it is bounded by its own coverage |
| The affected-file list is frozen at outline time | HYPOTHESIS | the freeze point, **by symbol** — ⛔ **D3's whole premise** |
| The three under-recording instances are one defect | HYPOTHESIS | ⭐ a 19-versus-37 gap, a 700-line approved-but-undeclared widening, and the general frozen-at-outline form. **The general form is the checkable one** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(a) must be seen to FAIL today.** A positive control that passes before the fix is not a control
  — it is a test of something else.
- ⛔ **D5(c) is what makes D1 a shared predicate rather than a local edit.** Running the control pair
  against only the first site would leave the second live and the suite green, which is this plan's own
  defect committed inside its fix.
- **D5(b), the matched negative control, guards the over-broad fix**: an untracked `.plan/` file must
  still be exempt, or every finalize starts reporting ordinary plan-state writes as offenders.
- **D2's population must be verified non-empty in the output**, not merely computed. A guard that
  publishes an empty population is honest but useless; one that publishes none is neither.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐ **The two independently-confirmed sites are the argument for the shared predicate.** They fail the
  same way for the same reason and were introduced separately — which is exactly the situation where
  fixing "the bug" fixes one instance.
- ⛔ **Do not go looking for the orchestrator spec, the absorbed spec, the drained messages, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. The one
  premise that **must** be re-derived from this clone — the tracked-file set under `.plan/` — is named
  in D0 and is a single command.
