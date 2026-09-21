# PLAN-TRUTH-177: orchestration detection fails open for a plan with no source_id

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.

## Objective

Forwarded from sibling epic `post-run-quality` (first-party confirmed on PLAN-PRQ-06,
PR #1541): `phase-1-init` writes no `source_id` for description-sourced plans — the
most common source — so the orchestration-verdict detector answers a confident "not
orchestrated" instead of "indeterminate", `emit-landing` never fires, and the owning
epic never receives its landing notification. Same shape as corpus lesson
`2026-09-09-06-001`, excluded there as fleet-wide rather than epic-specific; recorded
here because `truthful-signals` is this repo's standing owner of orchestrator-platform
mechanics on precedent.

## Deliverables

1. `phase-1-init` Step 5.1 writes a `source_id` section for every plan source,
   including `description` (today it writes `--source-id` only for `lesson`,
   `issue`, `recipe` and omits it for the default `description` source).
2. The orchestration-verdict detector fails CLOSED on an absent `source_id` —
   emits `detection: indeterminate` (a distinct `no_source_id` token, separate from
   `not_orchestrator_pointer`) rather than a confident `orchestrated: false` — and
   critically KEEPS `emit-landing` firing on the indeterminate case rather than
   suppressing it. Governing precedent: ADR-009 (status reporting fails closed with
   an explicit unknown state).
3. Optional third remedy, scoped as a stretch deliverable: `orchestrator inbox
   detect --plan-id` recovers the pointer from a plan's own hand-off command (the
   one-line `/plan-marshall task="implement {spec path}"` pointer every
   orchestrator-staged spec carries) as a fallback when `source_id` is absent but the
   plan was launched from an emitted orchestrator command.

## Claim Labels

- OBSERVED: `phase-1-init` Step 5.1 writes `--source-id` only for `lesson`, `issue`,
  `recipe` sources and explicitly omits it for `description` — read from the
  forwarding message's first-party confirmation on PLAN-PRQ-06 (PR #1541,
  `a1dd4901f`, `'source_id' in status.json.metadata` is `False`)
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: phase-1-init/SKILL.md:429 shows --source-id as OPTIONAL with placeholder set {lesson_id|issue_url|recipe_key}, and line 449 states it is only for traceable sources - description, the default, is omitted. NUANCE for D0: line 303 adds a FOURTH source that DOES pass one on the file-pointer branch, so the claim's three-member enumeration is incomplete even though its conclusion about description holds.
- OBSERVED: PLAN-PRQ-06's `emit-landing` never fired and `post-run-quality` never
  received its landing notification — 23 `candidate-lesson` messages had to be filed
  manually as a workaround — read from the forwarding message
  (`post-run-quality-001.md`)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: PLAN-PRQ-06's emit-landing non-firing and the 23 manually-filed candidate-lesson messages are reported by the forwarding message post-run-quality-001.md in a sibling epic's inbox; not cross-read here.
- Verify-first clause: confirm `phase-1-init` Step 5.1's current source-handling
  branch and the orchestration-verdict detector's exact decision point against HEAD
  at outline before scoping.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/**`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `orchestration-verdict detector` (verify-at-outline: the forwarding message names the detector's behaviour but not its exact module)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- OBSERVED: `test/plan-marshall/phase-1-init/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none known against the current live queue
- Adjacent to: PLAN-TRUTH-143's own Open Defect (dispatched terminal step missing
  declared runtime inputs, recorded in `epic.md`) — related orchestration-detection
  fragility theme, different mechanism (dispatch inputs vs. absent `source_id`)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-177-orchestration-detection-fails-open-without-source-id.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
