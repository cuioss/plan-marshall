# Landing Analysis: PLAN-10 — always_on is not a resolve

epic: operator-ux
workstream: WS-01-domain-resolution
pr: #1391 — https://github.com/cuioss/plan-marshall/pull/1391

> Landing record for one shipped plan. Lives at `landings/PLAN-10.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Provenance — reported and corroborated

Reported by landing message `always-on-is-not-a-resolve-012.md`, `inbox landing-check` →
**`complete: true`, `missing_keys[0]`**. Corroborated independently before any ledger write:

- `ci pr view --pr-number 1391` → `state: merged`, head `feature/always-on-is-not-a-resolve`,
  `merge_commit_sha: 87782159b4c8c71499d205abc65396b1ee5685f0`.
- `git log -1 main` → `87782159b fix(manage-config): stop treating always_on-only as plan
  evidence (#1391)`. In `main`.
- `git show --stat 87782159` → **8 files, +153 / −42**.
- `.plan/local/archived-plans/2026-09-03-always-on-is-not-a-resolve` exists.

**This is the first landing in the epic reported by its own plan and complete on arrival.** The
prior three were reconstructed or arrived late. Nothing here needed inference.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Replace the `if inclusion_union:` guard with a test on plan-specific evidence | shipped-as-specified | `_cmd_domain_detect.py:447` now reads `if glob_matched_set:`; the union is still computed at `:359` but no longer gates the zero-match path |
| 2. A distinguishable `reason` for the new path, kept separate from the other two | shipped-as-specified | `:475` emits `reason='over_provisioned_always_on_only' if always_on_set else 'over_provisioned_resolve'` — three states, three tokens, as the spec required |
| 3. State the project-evidence vs plan-evidence rule in the contract docs | shipped-as-specified | `standards/skill-domains.md` (+12/−1) and `manage-config/SKILL.md` (+4/−2) both in the diff; the rule is also stated in the script docstring at `:287` |

Both code deliverables were verified by reading HEAD, not by trusting the report.

### Surface: declared 5, realized 8 — and the delta is fully accounted for

The three undeclared files are `automatic-review/standards/sourcery.md`,
`test/plan-marshall/automatic-review/test_bot_registry.py`, and
`test_refusal_recovery_arming.py`. **This is not silent drift**: it is the operator-approved
mid-run scope deviation (see Routing below), and the plan reported it. Recorded here as an
accounted-for widening rather than as an under-declaration finding.

⚠ Note for cost attribution: the run's own headline calls this "a 5-file bug fix". Eight files
landed. The cost figures below are for the 8-file reality.

## Metrics and Anomalies

**Drained from `landing-facts` (schema `landing-facts/1`), `complete: true`.**

| Fact | Value |
|------|-------|
| Deliverables | 2 / 2 |
| Total tokens | 3,987,911 |
| Total wall | 44,454s (12h20m), 2h26m worked |
| 6-finalize alone | 2,476,740 tokens (62%) |
| Merge mechanism | merge queue |
| Steps reported | 23, of which 22 `done` and 1 `pending` |

- ⛔ **Cost is the dominant finding, and this landing supplies the MECHANISM the epic has been
  missing.** Prior landings recorded the symptom (finalize costing 3–5× execute); this one names
  the cause. HEAD moved **four times inside finalize** — `43ed295b` → `8827a7f2` → `487b0cc4` →
  `87782159` — and each move re-armed every head-bound step that had already passed:
  `pre-push-quality-gate` ×4, `finalize-step-simplify` ×4, `automatic-review` ×3, `ci-verify` ×2,
  plus four more at ×2. **Twelve step firings beyond first-fire**, for three implementation
  tasks. Promoted as corpus lesson `2026-09-03-19-005`; this is the attack surface if finalize
  cost is to come down.
- **`archive-plan` reported `pending`, resolved by observation** — the archived directory
  exists. Same structural blind spot as PLAN-07 (`emit-landing` at order 1000 cannot see a step
  at 1100); the token differs (`pending` here, `unknown` there) but the cause is identical.
- **Nine argparse rejections across four unique signatures**, two of them recurring from
  different dispatched envelopes 47 minutes apart. The `ci pr --plan-id` position trap is
  documented by name in `agent-behavior-rules.md` and was hit anyway — **including by the main
  orchestrator session**. Four of the run's candidate-lessons target this class.

## Routing and Merge Behavior

- Merged as `87782159` via the merge queue. Head branch `feature/always-on-is-not-a-resolve`.
- ⛔ **Reviewer coverage was near-zero, and the quorum does not contradict that.** The barrier
  passed on `participation_complete: true` / `proves: participation_only`. Behind it: `pr-agent`
  (the only required bot) `participated_but_empty`, `coderabbit` `absent`, `sourcery`
  `refused_hard` (cause `quota`, ETA ~3d17h). **Zero comments here means near-zero review, not a
  clean review.** `finalize-step-review-retrospective` reached the same conclusion independently
  and recorded `comparative_verdict: unmeasurable`. The plan and the retrospective agreeing from
  two directions is what makes this trustworthy rather than a single component's self-report.
- **Scope deviation, operator-approved in-plan.** Sourcery declined with a third unregistered
  wording, so no refusal arm fired and it was credited as participating in a review it declined.
  The operator chose fix-here-anyway over split, so `sourcery.md` (third `refusal_patterns`
  entry plus `rate_limit_eta_patterns`) and two tests landed on this PR. **Verified working in
  the same run** — the pre-merge re-fetch classified sourcery into `refused_bots` with cause
  `quota`.
- ✅ **This closes the epic's longest-running recurrence.** The sourcery false-participation
  defect had three recorded acceptances (`2026-08-25-09-012`, `2026-09-02-08-001`, and PLAN-07's
  third instance) with no remedy. It is now fixed and demonstrated. The two prior corpus lessons
  are candidates for retirement once a subsequent run confirms the fix holds.
- **Surface-collision check: the gate predicted correctly.** PLAN-10 ran alone; the five staged
  plans were all correctly sequenced behind it. No collision materialized because none was
  permitted.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-10 --status shipped`
- [x] row `pr` stamped — `#1391`
- [x] row `landing` stamped — `landings/PLAN-10.md`
- [x] row `plan_marshall_plan_id` already stamped — `always-on-is-not-a-resolve`
- [x] 10 inbox messages drained and archived (1 landing + 9 candidate-lessons)
- [x] 5 lessons promoted (`2026-09-03-19-003..007`), 4 discarded as duplicates
- [x] `2026-09-03-16-005` AMENDED — message `-011` refuted its monotonic-decrease proposal
- [x] Two new Open Defects recorded (gate/review ordering, `prune-local-and-remote-ref`)
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **The epic is UNBLOCKED.** PLAN-10 was the sole `launched` plan and every staged plan
  collided with it. With it shipped, `manage-config/SKILL.md` and `phase-1-init/SKILL.md` are
  free and the queue can emit again — the first non-shortfall round in five.
- **PLAN-03's premise should be re-grounded before it launches.** It narrows what PLAN-10 just
  widened, and PLAN-10 changed `_cmd_domain_detect.py` — PLAN-03's primary file. Its
  re-grounding verdicts were stamped against an earlier HEAD.
- **Two new defects, neither owned by this epic**, both routed to the finalize-machinery epic
  the operator authorized: the pre-push gate certifying a tree review never saw, and
  `prune-local-and-remote-ref` aborting on an already-deleted local branch.
- **The finalize-machinery epic is now due.** The operator authorized it conditional on PLAN-10
  landing. It has landed.
