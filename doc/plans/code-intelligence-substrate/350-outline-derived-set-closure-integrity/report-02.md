# Run report — 350-outline-derived-set-closure-integrity (run 02)

**Date (UTC):** 2026-08-18    **Branch:** `claude/derived-set-closure-integrity-3i53aj` (harness-assigned)
**PR:** _pending_    **Outcome:** _in progress_

This run **continues** run 01, which was halted by operator instruction before the PR cycle. Run 01's
per-deliverable record stays in [`report-01.md`](report-01.md); the state it was halted in is written
up in [`actual-state.md`](actual-state.md). This report covers only what run 02 did.

## How run 01's work was recovered

Run 01 executed on the harness-assigned branch `claude/derived-set-closure-integrity-g7n8x2`, which
that session was bound to. It committed and pushed nine commits and opened no PR. **That branch is
still on `origin`, untouched by this run.**

This session was handed a *different* harness-assigned branch,
`claude/derived-set-closure-integrity-3i53aj`, and the lane contract's rule is that a cloud session
keeps the branch it was assigned — the binding is what makes the run resumable after a VM reclaim.
Continuing on `g7n8x2` would have left every later commit on a branch this session's harness cannot
find. So run 01's nine commits were **rebased onto current `origin/main` and re-pushed as
`3i53aj`**, and the PR is opened from `3i53aj`.

The rebase was required, not cosmetic: `g7n8x2` branched from `eb0124c`, and `main` had since taken
`b199d94` (`chore(cloud-plan-lane): require snapshot-based restore for mutation sweeps`), so the two
had diverged and no fast-forward existed. `b199d94` touches only
`.claude/skills/cloud-plan-lane/SKILL.md`; the rebase was conflict-free, and every commit's tree is
preserved. The commit SHAs therefore differ from the ones `report-01.md` and `actual-state.md`
quote — those documents are corrected to the rebased SHAs rather than left naming commits that are
no longer on the branch under review.

## Verification round budget

Run 01 declared **4 rounds** before its first dispatch and ran three. Run 02 does **not** re-declare a
budget and does not extend it: it executes **round 4**, the final round of the budget run 01 declared,
and the loop ends there. Exhausting the budget is the STOP CONDITION whose autonomous fallback the
contract fixes — everything condition **A** forbids leaving open is fixed regardless of the budget,
and every surviving **B** finding is characterised and disclosed per instance.

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | project-local (`.claude/skills/`) | The run contract; loaded as the first action, before reading the plan. |
| `plan-marshall:ref-code-quality` | bundle path | Always. |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Always. |
| `plan-marshall:persona-implementer` | bundle path | The surface is production code. |
| `pm-dev-python:python-core` | bundle path | The surface is Python production code. |
| `pm-dev-python:pytest-testing` | bundle path | The surface includes Python tests. |

Loaded by **bundle path**, not by plugin notation: the `plan-marshall` plugin is not installed in this
cloud session. No skill was unobtainable by either route.

`pm-plugin-development:plugin-architecture` and `pm-documents:ref-asciidoc` were **not** loaded, for
the reason run 01 recorded: no bundle was structurally added or removed and no `.adoc` file is
touched.

## Deliverables

Run 02 adds no deliverable of its own. D0–D5 were built by run 01 and are recorded in
[`report-01.md`](report-01.md) § Deliverables; run 02's changes to them are only the round-4 fixes
listed under § Findings below.

## Bridge — a write outside this plan's own directory, disclosed

The diff contains one edit under `doc/plans/` outside this plan's directory:
`doc/plans/code-intelligence-substrate/280-outline-plan-scope-derivation-integrity/report-01.md`,
two lines.

It is **a link repair, not a status or bookkeeping write.** Step 3 moved this plan from
`350-outline-derived-set-closure-integrity.md` to `350-outline-derived-set-closure-integrity/plan.md`,
which broke the two links 280's report holds to its arm-A hand-over. Leaving them dangling would have
left 280's report making a false cross-reference — a condition-**A** defect this run's own move
caused. No ledger, no status file, and no other plan directory was touched.

A sweep for the pre-move path — `grep -rn '350-outline-derived-set-closure-integrity\.md'
--include=*.md .`, run at the moment of this claim — returns exactly **one** hit, and it is the
sentence above this one: the pattern quoted in this report's own prose. No live cross-reference to
the pre-move path survives anywhere in the tree, so the repair is complete rather than partial.
⚠ An earlier version of this paragraph claimed the sweep "returns nothing outside `plan.md`'s own
front matter". Both halves were false — the sweep does return a hit, and `plan.md` contains no
occurrence of the string and has no front matter naming it. It was written from expectation rather
than from the command's output, which is the defect this plan is about, committed in the report
that discloses it.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — **8 production scripts and 9
test modules**, re-derived by running that exact command at the moment of this claim — so the full
gate applies.

_The final `./pw verify` result is recorded here once round 4's fixes are in and the tree is
undisturbed; run 01 explicitly declined to record its last `SUCCESS` as the gate because a
verification sub-agent's mutation campaign was running on the same tree at the time._

## Findings

_Pending round 4._

## Reviewer participation

_Pending the PR._

## Cost

_Recorded before the merge gate._

## Contract check (Step 9)

_Recorded before the merge gate._

## What have we learned (Step 9)

_Recorded before the merge gate._

## Residue

_Recorded before the merge gate._
