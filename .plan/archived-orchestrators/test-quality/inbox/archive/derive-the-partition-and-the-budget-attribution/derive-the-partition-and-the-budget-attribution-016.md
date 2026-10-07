envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=landing
created=2026-08-25T09:09:17Z
revision=1
amended=2026-08-25T09:11:06Z

# Landing: PLAN-120 — Derive the partition and the budget attribution

```landing-facts
schema=landing-facts/1
plan_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
pr=#1345
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=6520174
total_wall_seconds=91980
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,finalize-step-security-audit:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,sonar-roundtrip:done,adr-propose:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
step.pre-submission-self-review.firing_count=4
step.project:finalize-step-plugin-doctor.firing_count=3
step.pre-push-quality-gate.firing_count=6
step.finalize-step-simplify.applied_edits=7
step.finalize-step-security-audit.findings=0
```

> `archive-plan:pending` is honest rather than optimistic: `emit-landing` is
> ordered BEFORE `archive-plan` by construction, so that step genuinely has not
> run at emission time. `total_tokens` spans more than one population (see the
> metrics Phase Breakdown note) and is not a dispatched-subagent total.

## Outcome

Merged. PR #1345, squash-merged via the merge queue onto `main` at `00b92fca`.
All three deliverables (D1 spec parser + three-class classifier, D2 partition +
budget attribution with injected-failure controls, D3 seven-section report)
fulfilled at 100% declared-mutation-file coverage. 14 files landed against 10
declared; the 4 extras are all inside the plan's own new skill tree and 3 of
them are additional test modules.

## Where it landed

New skill `pm-plugin-development:tools-epic-surface-partition`, NOT a
`plugin-doctor` subcommand. The spec left placement as a gating
`verify-at-outline` hypothesis; it was settled on `plugin-doctor`'s own declared
model, which registers only `doctor-marketplace.py` and scopes its scripts to
marketplace-component rules. An orchestrator-ledger derivation tool is not a
marketplace-component rule.

The `marketplace/bundles/**` overlap the spec flagged is **LIVE, not inert** —
the standard placed the checker inside WS-03's tree. The overlap is confined to
new files plus a one-line `plugin.json` registration.

## Derived results that DISAGREE with the spec's own prose

The spec said "re-derive it; do not trust it". The re-derivation disagreed, and
the disagreements are reported rather than silenced:

- **Budget attribution: 271 over-budget modules, not the stated 267** (+4).
- **Provenance: 18 live `marketplace/bundles/**` overlaps** across
  PLAN-010 / 090 / 105 / 145 / 165. The outline predicted PLAN-145 / 160 / 105 —
  and **PLAN-160 carries no bundle-tree claim at all**.
- The residual `multiply_claimed` population is a genuine PLAN-080 / PLAN-140
  corpus overlap, not a parser artifact.

## No inbox message was owed for the test location

PLAN-080's Expected Surface already claims `test/pm-plugin-development/**`
recursively, which covers the new skill's mirror directory. The D3 escalation
branch resolved to NO-CONTRADICTION and was confirmed against an empty inbox at
the time. No spec under `.plan/orchestrator/` was edited by this plan.

## A correctness defect the plan's own subject matter predicted

`_raw_mentions_module` anchored every unresolved span on the module FILENAME
(`target[-len(pattern):]`). A directory-shaped span — `.../workflow-integration-github/`,
the corpus's own documented relative-continuation notation — has a directory name
as its last segment, which can never equal a filename, so it matched no module
and every module beneath it fell through to `unclaimed`.

That is exactly the merge D2 forbids: coverage the parser cannot see, reported
as a partition defect it manufactured from its own limits. Fixed with paired
positive and negative controls over both container shapes; falsifiability
executed (3 of 5 controls fail with the fix disabled). The real `test-quality`
corpus renders identically — its three unresolved spans are all file-shaped — so
the fix restores the contract without moving any published figure.

## Review record

- Pre-submission self-review fired 4 times (failed, failed, failed, done) and
  found 7 defects, including the one above, which no review bot found.
- Review bots found 3 defects the in-house gates passed. Two of those fall
  inside `ext-self-review-plan-marshall`'s own declared candidate classes, yet
  its pass reported "301 candidates examined, no check matched".
- Neither channel subsumes the other.
- One loop-back iteration (ceiling 3). CI green at both `1873bd9a` and the
  post-fix `598fc22b`.

## Residue

Facts no finalize step recorded, carried as prose rather than fabricated into
typed facts:

- **Scoped `plugin-doctor` structurally cannot evaluate cross-skill rules** whose
  finding anchors outside `--paths`. Whole-tree CI was the real check and passed.
  The step's own clean verdict covers skill-local rules only.
- **The self-review pass reaches internal consistency between statements present
  in the diff**; it does not evaluate behaviour under inputs the diff does not
  contain. `301 candidates examined` is a volume, not a coverage number.
- **`scope_creep_check` returned `reason: no_baseline_sha`** — `residual_count: 0`
  is an ABSENT measurement, not a clean one.
- **`adr-propose` produced two ADR drafts it could not create**: the step mandates
  operator confirmation and a dispatched leaf cannot fire `AskUserQuestion`. The
  drafts were neither auto-created nor discarded as "none proposed"; they await
  an explicit operator decision.
- **The plan spans two sessions.** `status.metadata.session_ids` records one; the
  forwarded session id resolved to no transcript, and metrics enrich only
  succeeded against the other.

## Candidate lessons filed separately

15 `candidate-lesson` messages are queued in this epic's inbox (8 from
plan-retrospective, 7 from lessons-capture). Messages 001 and 010 are best read
together — they share `compute_plan_branch_diff` and the second explains an
inflation the first may be observing.
