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

# A foreign task reports done with no PR anywhere, because done-ness is measured at the commit

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

Task done-ness is measured **at the commit**. That is correct for a host task, where the plan's own PR
carries the commit into review and merge. It is structurally wrong for a **foreign** task — one whose
change lands in a different repository — because nothing carries that commit anywhere: it sits on a
branch in another repo with no PR to review or merge it.

On one recent plan this nearly cost three of eight deliverables. Finalize completed with **four foreign
branches committed and pushed and zero pull requests opened**, and every task reported `done`. The host
PR merged, branch-cleanup ran, and the plan advanced to archive.

⭐ **The awareness was never missing.** The request carried an explicit foreign-repo warning
instructing each foreign change to *"land as its own PR in its own repository"*, and phase 5 recorded
the shortfall correctly and three times — each artifact line ending in the literal words **"PR not yet
opened"**. The fact was observed, correctly worded, and written to the work log three times.

⛔ **The gap is purely that nothing reads it.** A signal that is written and read by nothing is this
epic's own theme — a confident signal hiding a caveat — reappearing at the task layer.

## Goal

A foreign task cannot reach `done` while its change has no pull request, and the state it rests in
instead is distinguishable from both `done` and an ordinary failure. The condition is enforced by a
deterministic verb that a gate calls, not by prose in an artifact that no gate reads.

## Deliverables

Three. Deliberately under the six-deliverable split heuristic.

1. **D0 — GATE, mutates nothing: settle whether a foreign task is distinguishable from a host task at
   the moment `done` is written.** Read the task record schema and the completion path. Report whether
   the record carries a repository-target field, or any signal from which foreign-vs-host is derivable
   (an `affected_files` path outside the project root is the candidate).
   ⛔ **This deliverable HALTS the plan.** If the distinction is not derivable at the point completion
   is recorded, **say so and stop** — D1 would then have to add a field to the task schema first, which
   is a change with its own blast radius and must be re-scoped as its own plan rather than absorbed
   here.
   ⛔ **Do not hand-enumerate the task kinds that can target a foreign repository.** Derive the
   population; if it cannot be derived, that is the halt condition above.
   *Done when:* the report states the discriminator, where it is read, and the derivation method — or
   states that no discriminator exists and the plan stops.

2. **D1 — a foreign task's done-ness is measured at the PR, not the commit.** A foreign task whose PR
   does not exist is not `done`.
   ⭐ **Implementation shape is already settled — adopt it rather than re-deriving one.** Add a
   deterministic backing verb, `ci pr landing-state --project-dir P --branch B`, returning exactly one
   of `merged` / `pr_open` / `pushed_no_pr` / `unpushed`. The four-step sequence it automates has
   already been run by hand and is fully deterministic: `git status --porcelain --branch`,
   `git branch -r --contains`, `ci pr list`, then correlate the head branch. This is transcription, not
   design.
   Then gate on it: before `archive-plan`, for every deliverable whose declared `affected_files`
   contains a path outside the project root, resolve that repository's landing state and **refuse to
   archive while any is `pushed_no_pr`.**
   *Done when:* the verb exists with a test per return value, and a plan with a `pushed_no_pr` foreign
   deliverable is refused at archive, proven by a test that fails before the change.

3. **D2 — the recorded-but-unread gap line becomes a gate input, or is replaced by something that is.**
   Phase 5 already emits *"PR not yet opened"* into the artifact. **Prose that no gate reads must not be
   the record of a blocking condition.** Either that line becomes a consumed signal, or it is replaced
   by a structured field the gate reads and the prose stops carrying the obligation.
   ⚠ Rides along, and it is a second defect in its own right: `manage-solution-outline
   list-deliverables` should emit a `foreign: true/false` column per `affected_files` entry. Without it
   the gate has no population to iterate **and every coverage ratio silently pools host paths with
   foreign ones** — the plan whose failure motivated this one pooled 23 host paths with 8 foreign ones
   in its own coverage figures.
   *Done when:* a gate reads a structured signal rather than the artifact prose, and the coverage
   column distinguishes the two populations.

## Out of scope

- **The landing-message composition site**, including the multi-emission defect the same run exposed
  (three `landing` messages emitted as the outcome kept changing, only the last authoritative, with
  nothing in the channel saying so). It belongs to a separate plan in this epic. ⛔ Two plans staged
  against one seam is the duplicate-spec trap. ⚠ The shared root cause — *an outcome declared final
  before it was* — is worth carrying in both, but this plan removes the mechanism and does not touch
  the message.
- **Unblocking the parked foreign-repo bookkeeping plan.** That needs source work in another
  repository, which this plan does not do. D1 removes the mechanism that produced it; the parked plan
  stays parked.
- **`phase-6-finalize`'s merge-lock and branch-cleanup surfaces.** Adjacent, untouched — a change there
  would collide with other staged plans in this epic.
- **Any change to another repository.** This plan's diff is entirely in this repo. The one foreign
  interaction it contemplates is read-only (see D3 note under Verification).

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-tasks/` — the completion seam.
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — the task runner that records `done` and
  emits the *"PR not yet opened"* artifact line.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the foreign-PR creation path and the
  finalize-completion condition, plus the pre-`archive-plan` gate position.
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — where the `landing-state` verb
  lands. ⚠ Note the CI router already accepts a `--project-dir` flag consumed **before** dispatch
  rather than declared in an argparse table; verify the flag against the router, not the argparse
  table, before concluding it is absent.
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/` — the `foreign:` column.
- The matching `test/plan-marshall/...` trees for each.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Finalize completed with four foreign branches pushed, zero PRs opened, and every task reporting `done` | OBSERVED | Restated here in full; the originating run report is machine-local and not in your clone |
| The gap was recorded three times as *"PR not yet opened"* and read by no gate | OBSERVED | The phase-5 artifact-line emission site — find the literal string in `phase-5-execute` and enumerate its consumers |
| Task done-ness is decided at a **single, locatable seam** rather than distributed across per-task-kind logic | HYPOTHESIS | The `manage-tasks` completion path and the `phase-5-execute` task-runner that records `done`. ⛔ If it is distributed, D1 re-scopes from *change the seam* to *derive the population of seams*, which is a materially larger plan — report it and propose the split rather than absorbing it |
| A foreign task is distinguishable from a host task at the point completion is recorded | HYPOTHESIS | The task record schema. **This is D0 and it gates the plan** |
| The four-step landing-state sequence is fully deterministic | OBSERVED | It was executed by hand across four checkouts; the four commands are named in D1. Re-run them once against this repo to confirm the shape before building on it |

⚠ **Every count here is a lead.** Four branches, three log lines, 23-vs-8 paths — all are observations
from one past run, not properties of the tree you clone. **Re-derive anything you intend to assert.**

⛔ **Do not go looking for `.plan/`.** The orchestrator ledger, the plan specs, and the run report that
evidenced this plan are git-ignored and **absent from your clone**. Everything this run needs is in
this file.

## Verification

- Run the repository's full verify. Read the result payload's `status` and `errors[]` — the build
  wrapper exits 0 even on failure.
- **Every test proven to fail before the fix.** In particular the archive-refusal test: confirm a
  `pushed_no_pr` foreign deliverable is archived today and refused after.
- **`landing-state` gets one test per return value** — `merged`, `pr_open`, `pushed_no_pr`, `unpushed`
  — and the population of return values is asserted against the verb's own declared set, not
  hand-listed in the test.
- ⭐ **Cold read of the gate's refusal text.** D1 introduces a refusal at archive and D2 changes what a
  reader is told about an unlanded foreign change. Have the pre-PR verification sub-agent read the new
  text **cold** and report whether it takes the condition as *blocking*, *advisory*, or *informational*.
  If the cold reading is not "blocking", the wording failed however correct the code is.
- ⚠ **An owed check this plan carries so it cannot lapse — and it is conditional.** A prior plan shipped
  a language-specific reviewer instruction pack and left its confirm/refute check **unrun**: re-review a
  closed Java pull request that another reviewer found in-charter defects on — `cuioss/API-Sheriff`
  **#185** (26 inline items) or **#154** (47) — with the shipped pack installed, and compare against
  this reviewer's **recorded zero** on those same diffs.
  ⛔ **That repository is not yours and this plan changes nothing in it — the check is read-only.** It
  is also **not reachable from your clone**, and you have no operator to grant access. So: attempt it
  only if that repository is readable from this run; if it is not, **record in the report that the
  check remains owed, restate the procedure above verbatim so it cannot lapse, and continue.** Do not
  report the plan complete in a way that implies the check ran.
  ⛔ **A refutation is a publishable result, not a failure** — it would mean the Java blind spot has a
  cause the pack does not address, which is more valuable than another untested remedy.

## Notes

- **Sequencing.** No dependencies. Adjacent to the merge-lock and branch-cleanup surfaces, which other
  staged plans in this epic claim — keep out of them.
- **Why the split guard was respected here.** An earlier draft carried a fourth deliverable that
  duplicated another plan's subject; it was moved rather than kept. Three deliverables is deliberate,
  and the earlier override of the split guard elsewhere in this epic is not precedent.
- **The root cause worth carrying.** An outcome was declared final before it was. That single fact
  produced both this plan's defect and the multi-emission defect now owned elsewhere. If D0 or D1
  surfaces evidence bearing on the message half, **record the verdict in the run report** so it reaches
  the other plan — do not act on it here.
