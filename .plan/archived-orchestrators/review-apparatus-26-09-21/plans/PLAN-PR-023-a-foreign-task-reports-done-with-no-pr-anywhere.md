# PLAN-PR-023: A foreign task reports done with no PR anywhere

epic: review-apparatus
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

Task done-ness is measured **at the commit**. That is correct for a host task, where the plan's PR
carries the commit into review and merge. It is structurally wrong for a **foreign** task, where
nothing does: the commit lands on a branch in another repository and no PR exists to carry it.

On PLAN-PR-022 this nearly cost three of eight deliverables. Finalize completed with **four foreign
branches committed and pushed and ZERO pull requests opened**, and every task reported `done`. Phase 5
recorded the gap correctly and three times — each artifact line ending in the literal words *"PR not
yet opened"* — and **no gate reads that line**.

This plan makes a foreign task's completion contingent on a PR existing. It also carries the **unrun**
confirm/refute check PLAN-PR-022 left open, so that HYPOTHESIS cannot lapse silently. ⛔ The related
multi-emission defect the same run exposed is **NOT** in scope here — it moved to PLAN-PR-010 at
staging (§ Dependencies).

## Deliverables

Three. Deliberately under the split guard — the PLAN-PR-022 override is not precedent.

1. **A foreign task's done-ness is measured at the PR, not the commit.** Derive the population of
   task kinds that can target a foreign repository; do not enumerate by hand. A foreign task whose PR
   does not exist is not `done`, and the resulting state must be distinguishable from both `done` and
   an ordinary failure.
2. **The recorded-but-unread gap line becomes a gate input.** Phase 5 already emits *"PR not yet
   opened"* into the artifact. A signal that is written and read by nothing is the epic's own
   confident-signal-hides-a-caveat theme at the task layer. Either the line gates, or it is replaced
   by something that does — **prose that no gate reads must not be the record of a blocking
   condition.**
3. **Run the PLAN-PR-022 confirm/refute check and record the result either way.** Re-review a closed
   Java pull request that CodeRabbit found in-charter defects on — **API-Sheriff#185** (26 CodeRabbit
   inline items) or **#154** (47) — with the shipped instruction pack installed, and compare against
   this reviewer's **recorded zero** on those same diffs. ⛔ A refutation is a publishable result, not
   a failure: it would mean the Java blind spot has a cause the pack does not address, which is more
   valuable than another untested remedy.

## ⭐⭐ ABSORBED 2026-08-09 — the plan's own retrospective supplies the mechanism AND the verb

Source: inbox `generic-charter-language-specific-defect-001`, first-party, `confidence: high`,
`component: plan-marshall:phase-6-finalize`.

**Verified at retrospective time across all four foreign checkouts**: every branch pushed and in sync
with origin, `git branch -r --contains` reporting each commit on its feature branch **only**, and
`ci pr list --state open` returning **zero** PRs for any of the four. Tasks 9, 10 and 11 reported
`done` at 1/1, 2/2 and 4/4. The host PR merged, branch-cleanup ran, and the plan advanced to archive.

⭐ **The awareness was never missing** — the request carried an explicit `Foreign-repo warning`
instructing each foreign change to *"land as its own PR in its own repository"*, and phase 5 logged the
shortfall three times. ⛔ **The gap is purely that nothing reads it.** *"The fact was observed,
correctly worded, and written to the work log three times."*

### Three concrete proposals, adopted into the deliverables

1. **A foreign-landing gate before `archive-plan`**: for every deliverable whose declared
   `affected_files` contains a path outside the project root, resolve the target repository's landing
   state and **refuse to archive** while any is `pushed_no_pr`.
2. ⭐⭐ **Give it a deterministic backing verb rather than prose** — `ci pr landing-state --project-dir P
   --branch B` returning one of `merged` / `pr_open` / `pushed_no_pr` / `unpushed`. **The four-repository
   sequence this retrospective ran BY HAND is fully deterministic** (`git status --porcelain --branch`,
   `git branch -r --contains`, `ci pr list`, correlate head branch) — so this is transcription, not
   design. ⇒ **This is D1's implementation shape; adopt it rather than re-deriving one.**
3. **`manage-solution-outline list-deliverables` emits a `foreign: true/false` column** per
   `affected_files` entry, so the gate has a population to iterate **and every coverage ratio stops
   silently mixing 23 host paths with 8 foreign ones.** ⭐ That last clause is a second defect in its own
   right — the plan's own coverage figures pooled two populations.

⇒ D1's HYPOTHESIS about a single locatable seam is **partly settled**: the gate belongs at
phase-6-finalize before `archive-plan`, and the population comes from `affected_files` path analysis.
⚠ Still unsettled and still verify-at-outline: whether the **task record** can distinguish foreign from
host at the point `done` is written, which is what D1's second half needs.

## Claim Labels

- OBSERVED: finalize completed with four foreign branches pushed and zero PRs opened, every task
  reporting `done`, and the gap recorded three times as *"PR not yet opened"* — operator run report
  for PLAN-PR-022, corroborated by the host PR merging at 16:17:06Z while all four foreign PRs merged
  at 18:19:32–18:36:29Z (`gh pr view --json state,mergedAt`, this orchestrator, first-party).
- OBSERVED: three `landing` messages from sender `generic-charter-language-specific-defect` at
  17:04:41Z, 17:52:24Z and 18:38:03Z — read first-party from `orchestrator inbox list --slug
  review-apparatus`.
- OBSERVED: all five PLAN-PR-022 landings are MERGED — plan-marshall#1130 `f5493b437`,
  pr-agent-settings#14 `1cc5af4ec`, cuioss-organization#237 `7dc1890f0`, TokenSheriff#643 `2297e081c`,
  API-Sheriff#202 `3e8f7a73f`.
- OBSERVED: the Java confirm/refute check named in PLAN-PR-022's spec was NOT run — stated by the run
  report and not contradicted by any artifact.
- HYPOTHESIS: task done-ness is decided at a single, locatable seam rather than being distributed
  across per-task-kind logic — confirm/refute at the `manage-tasks` completion path and the
  `phase-5-execute` task-runner that records `done` (verify-at-outline). If it is distributed, D1
  re-scopes from *"change the seam"* to *"derive the population of seams"*, which is a materially
  larger plan and may warrant a split.
- HYPOTHESIS: the three landing emissions and the missing foreign PRs share ONE root cause — an
  outcome declared final before it was — rather than being two independent defects. Confirm/refute by
  reading the three message payloads against the finalize step order (verify-at-outline). This matters to PLAN-PR-010, which now owns the
  message half; record the verdict there as well as here.
- Verify-first clause: D1's premise is that a foreign task is *distinguishable* from a host task at
  the point completion is recorded. Settle that against the task schema before scoping — if the task
  record carries no repository-target field, D1 must first add one, and that is a schema change with
  its own blast radius.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/` — the completion seam
  (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — the task runner that
  records `done` and emits the *"PR not yet opened"* artifact line (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the foreign-PR creation
  path and the finalize-completion condition (verify-at-outline)
- OBSERVED: `cuioss/API-Sheriff` PR #185 or #154 — READ-ONLY re-review target for D3; this plan
  changes nothing in that repository
- ⛔ NOT IN SURFACE: the landing-message composition site. It belongs to PLAN-PR-010 (see
  § Dependencies) and this spec must not touch it.

## Dependencies and Sequencing

- Depends on: none.
- ✅ **PLAN-PR-010 overlap RESOLVED at staging, not deferred.** The draft carried a fourth
  deliverable (*one landing message per landing*) that duplicated PLAN-PR-010's subject. It has
  been **moved to PLAN-PR-010** together with its first live instance — PLAN-PR-022 emitted
  THREE `landing` messages (17:04:41Z, 17:52:24Z, 18:38:03Z) as its outcome kept changing, only
  the last authoritative and nothing in the channel saying so. ⛔ Two plans staged against one
  seam is the duplicate-spec trap; this spec no longer touches the landing-message surface.
  ⚠ The shared ROOT CAUSE remains worth carrying in both: an outcome declared final before it
  was. D1 removes the mechanism; PR-010 handles the message the mechanism produced.
- Overlaps with: PLAN-PR-002 — parked on the same foreign-repo bookkeeping class. This plan does not
  unblock it (that needs source work in `cuioss-organization`), but D1 removes the mechanism that
  produced it.
- Adjacent to: `phase-6-finalize`'s merge-lock and branch-cleanup surfaces — untouched here.
- ⚠ **The host PR for this plan is a plan-marshall change**, so unlike PLAN-PR-022 it carries no
  foreign-repo host-PR hazard. D3 is a read-only re-review in a foreign repo and produces no diff
  there.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-023-a-foreign-task-reports-done-with-no-pr-anywhere.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
