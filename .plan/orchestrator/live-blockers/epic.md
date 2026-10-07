# Epic: Live Blockers

slug: live-blockers

> Hand-written narrative for one epic under `.plan/orchestrator/live-blockers/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. The ledger JSON files
> (`status.json`, the `queue/{PLAN-ID}.json` rows) and `resume_anchor.md` are the machine
> authority; any statement here that conflicts with them is stale prose.
>
> START HERE and the Ordered Queue are not in this file. They live in the generated,
> git-tracked `queue-view.md` next to it (see the Persist / Stop-Resume Contract in that
> standard). `queue-view.md` is never hand-edited. A merge conflict in it is never merged by
> hand: merge the source files, run
> `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view --slug live-blockers`
> on the merged tree, and `git add` the result.

## Vision

plan-marshall's workflow machinery is being rewritten as plan-marshall-mcp, and until that ships
plan-marshall stays in daily production use. This epic holds the work that cannot wait for the
rewrite: defects that make a normal plan run fail, mislead or need an operator override today,
and high-priority work on things the rewrite does not replace — harness sync, organisation CI,
the review bots and their rollout. It is too large for one plan because the 21 fixes sit on
different surfaces and most are independently shippable. The epic is done when a plan can run
from init to merge in this repository and in a consumer repository without a manual override,
and the review gate can be trusted to mean what it says.

The epic was cut on 2026-10-07 from a sweep of the nine epics active at the time and the lessons
store. Eight of those epics were closed and archived in the same act; `lessons-routing` stays
active. Design input for the rewrite is not carried here: it lives in plan-marshall-mcp's
requirements, specification and implementation-watch documents.

## Queue annotations

- PLAN-LB-02, PLAN-LB-03 — both edit `phase-6-finalize/workflow/pre-submission-self-review.md`;
  run them one after the other, never together. LB-03 is the smaller change.
- PLAN-LB-05, PLAN-LB-18 — both touch the review step's waits. LB-05 owns the short pacing
  sleeps and the timeout classification; LB-18 owns the CodeRabbit rate-window wait and the
  notice parsing.
- PLAN-LB-14 — the launch gate this plan fixes also gates this epic's own `next`. Until it
  lands, expect `next` to refuse on an indeterminate comparison and each launch to need an
  operator override. That argues for running it early.
- PLAN-LB-16, PLAN-LB-20, PLAN-LB-21 — mostly work in other repositories
  (`cuioss-organization`, the consumer fleet, `cuioss-review-bot`). They declare little or no
  surface in this repository, so the disjointness gate cannot order them against each other;
  LB-21's measurement should inform LB-20's rollout.

- **Queue order** is staging order: PLAN-LB-14 first because it unblocks `next`, then the
  small ready fixes (LB-01, LB-04, LB-07), then LB-03 before LB-02, LB-05 before LB-18, LB-18
  before LB-19, and LB-21 before LB-20.
- **Operator decisions the specs leave open** (each is a verify-first clause in its spec):
  - PLAN-LB-14 — whether a sibling spec that is only `staged` or `parked` can block a launch.
  - PLAN-LB-02 — how a plan already in finalize is read once the loop counter is per source.
  - PLAN-LB-03 — "done, not covered" with a warning, or halt and ask.
  - PLAN-LB-04 — write the PR title before the refine boundary, or defer the check to outline.
  - PLAN-LB-08 — sticky resolutions with an opt-in reopen of `fixed`, or always reopen `fixed`.
  - PLAN-LB-11 — how legitimate out-of-footprint edits by finalize steps get in.
  - PLAN-LB-13 — what replaces `test -pl X -am` for modules using a sibling test-jar.
  - PLAN-LB-15 — whether the sync may write Claude Code's plugin registry.
  - PLAN-LB-16 — what to do if the organisation workflow release is not available.
  - PLAN-LB-19 — whether Sourcery may lose its credit when its review is not of the merge commit.
  - PLAN-LB-20 — the two `project.yml` schema decisions and cutting an organisation release.
  - PLAN-LB-21 — running `gh`-based corpus scripts, posting `/review` on merged PRs, and the
    roster decision itself.

## Decisions

- 2026-10-07 — **Epic created by operator instruction** ("create an orchestrator for the
  critical / high; remove them from the current orchestrator; archive / dormant the other
  orchestrators beside lessons-routing"). Scope is the 21 high-priority clusters of the
  cross-epic sweep; the roughly 50 medium and low clusters are recorded in `backlog.md` and are
  not staged. Alternative considered: stage all 70 — not chosen, the operator asked for
  critical and high only.
- 2026-10-07 — **parallelization_scope set to 2** (operator choice over the project default
  of 1). Most plans share finalize files, so truly disjoint pairs will be limited; two lets a
  CI or review-bot plan run beside a finalize plan.
- 2026-10-07 — **Specs re-drafted, not copied.** Where an earlier epic already had a spec for
  the same fix, its analysis was reused but every claim was re-read against HEAD and the scope
  cut to what removes the blocker, because the source specs were up to three weeks stale and
  bundled unrelated deliverables. Each spec names the source plan ids it carries forward.
- 2026-10-07 — **Decomposed into 5 workstreams and 21 staged plans.** Spec bodies were drafted
  by five read-only agents against HEAD `6edefac32` and adjudicated here: all 21 resolve a
  declarative surface with no unresolved entry, none exceeds five deliverables, and none was
  found already fixed. Scope-bloat guard: no split needed. Two specs were amended after
  drafting — PLAN-LB-14's store figures (measured while the archived root was missing) and
  PLAN-LB-11 (the #1700 deletion as evidence).
- 2026-10-07 — **`.plan/archived-orchestrators/` restored.** PR #1700 had deleted all 2038 files
  of the archived-epic tree from `main` as a side effect of a five-file fix. Restored
  byte-identical from `78ba60f41^` in the ledger worktree before the eight closed epics were
  archived into it. Not confirmed with the operator as accidental at the time of writing.

## Open Defects

- **Medium and low items are not owned by any staged plan.** They are listed with evidence
  in `backlog.md` (sections 1.12 onward, 2.3 onward, 3.2 onward, 4.7 onward and 5). Promote an
  item into a plan spec when it starts to hurt; re-verify it at HEAD first.
- **35 active lessons have no router of their own beyond `lessons-routing`**, which was
  dormant at the cut. The lessons that describe live defects are folded into the specs here
  and into `backlog.md`; two lessons describe defects already fixed and should be retired
  (`2026-09-27-07-001`, `2026-10-02-21-006`), and `2026-09-27-19-001` has no metadata header.
  — source: sweep of the lessons store, 2026-10-07.

## Watches

- **Harness installs lag the source after every landing** until PLAN-LB-15 ships: the plugin
  registry pin is behind the executor. A session may run stale skill text. — trigger: before
  trusting a skill's behaviour right after a landing, compare the registry pin with
  `MARSHALL_VERSION`; retire when PLAN-LB-15 lands.
- **`plan-pr-078-review-bot-fleet-opt-in` is still listed as in progress at finalize** with a
  dead worktree pointer and its archive step never run; four consumer checkouts are still on
  its merged branch. — trigger: clean up by hand or when the worktree-pointer fix
  (`backlog.md` § 1.14) is promoted.
