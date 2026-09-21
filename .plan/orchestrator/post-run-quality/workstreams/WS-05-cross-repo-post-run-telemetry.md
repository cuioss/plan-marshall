# WS-05: Cross-repo post-run telemetry

epic: post-run-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-cross-repo-post-run-telemetry.md` and is tracked
> in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Today `archived-plans/` and `archived-orchestrators/` live inside each project's own
`.plan/local/`, subject to that project's own retention/GC and invisible to any query
spanning more than one repo; the only corpus-level quality auditor
(`.claude/skills/audit-archived-plan-retrospectives`) lives inside THIS repo and can only
be pointed at this repo's own archive. This workstream owns standing up a new,
`plan-marshall-telemetry` repository as the durable, cross-project home for that archived
data, the machinery that moves it there, and the machinery that analyzes it once there — so
a retrospective finding survives past any one project's local GC and a quality report can be
produced identically whether it runs at finalize time inside a project or after the fact
against the telemetry archive. It closes when the new repo exists, is populated by at least
one real transfer, and both analysis paths (in-repo finalize step, telemetry-repo skill)
produce structurally identical reports.

## Scope

- In scope: scaffolding the `plan-marshall-telemetry` repo (main-only, no review-bot
  onboarding); its `transfer` project-level skill; its `analyze` project-level skill; the
  new `analyze-marshall-quality` finalize step in this repo; relocating
  `.claude/skills/audit-archived-plan-retrospectives` into the telemetry repo.
- Out of scope: fixing defects INSIDE `audit-archived-plan-retrospectives`'s own checks or
  its census/quality-chain logic — owned by WS-01 (PLAN-PRQ-01) and WS-02 (PLAN-PRQ-03) and
  consumed here only after they land; reviewer-quality measurement (owned by the
  `review-apparatus` epic — the PR test wins outright); the lessons corpus itself (WS-03 /
  PLAN-PRQ-05).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PRQ-07-cross-repo-telemetry-archive-and-analyze | staged | New `plan-marshall-telemetry` repo + transfer/analyze skills + finalize step + relocation of the existing auditor |

## Sequencing and Surface Notes

- PLAN-PRQ-07 MUST sequence strictly after PLAN-PRQ-01 and PLAN-PRQ-03 land — both touch
  `.claude/skills/audit-archived-plan-retrospectives/**`, the exact skill PRQ-07 relocates.
  Relocating it out from under either plan's in-flight edit is a collision no gate can see
  because the two plans are in WS-01/WS-02, not WS-05.
- If the new `analyze-marshall-quality` finalize step lands marketplace-bundled (pending
  outline-time confirmation — see the spec's Claim Labels), it shares
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` with PLAN-PRQ-04 and
  PLAN-PRQ-06 — never pair PRQ-07 with either while that surface is in flight.
