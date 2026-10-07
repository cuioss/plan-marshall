# Landing Analysis: PLAN-28 — Lessons-Housekeeping ↔ Plugin-Doctor Contract

epic: plan-optimization
workstream: WS-10
pr: #962 (`cd931fb63`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

All three deliverables corroborated against the merge commit `cd931fb63`
(12 files, +873/-17). No claim in the operator narrative failed verification.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — drop the in-prose lesson-ID mandate from promote-then-retire | shipped-as-specified | `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` (+39/-…); the `(extends lesson {id})` / `(promoted from lesson {id})` citation mandate is gone. Provenance relocated to the retirement tombstone + decision log, so `no-lesson-id-in-skill-prose` stands unweakened — the contradiction was resolved in favour of the lint, not by carving an exception into it |
| D2 — move the step into the pre-merge settle band (996 → 4) | shipped-as-specified | Same SKILL.md plus `extension-api/standards/ext-point-finalize-step.md` (+8). Step now `order: 4` with `mutates_source: true`, so its edits ride the dispatcher's **existing** pre-merge commit instrumentation — no new mechanism introduced |
| D3 — structural guard against silent re-divergence | shipped-as-specified, **scope exceeded favourably** | New analyzer `_analyze_mutates_source_order.py` (+307), wired into `_rule_registry.py`, `_runner.py`, `doctor-marketplace.py`; documented in `rule-catalog.md` + `rule-provenance.md`; covered by `test_analyze_mutates_source_order.py` (+388), `test_analyze_lesson_id_in_skill_prose.py` (+87), `_fixtures.py`, `test_runner.py`. The merge-gate order is resolved **dynamically** from the discovered `branch-cleanup` rather than hardcoded — a more durable guard than the spec required |

**Self-validation.** The strongest evidence is behavioral, not textual: the step ran during
this plan's own finalize and left a clean tree. The plan eliminated the exact wedge it was
chartered to eliminate, on itself, in the same run.

## Metrics and Anomalies

- Tokens: 3.9M
- Duration: 1h56m worked
- Finalize: 22/22 steps done; whole-tree plugin-doctor gate 0 violations;
  pre-submission self-review 48 candidates / 0 findings; `finalize-step-simplify` 0 edits
- Deploy: 1105 files, bundles → **v0.1.1173**; plugin cache synced (10 bundles) + executor regenerated
- Anomalies (3, all diagnosed rather than retried — see Routing):
  1. **`status: timeout` that was not a timeout.** Log showed `1868 passed in 62.47s`; the
     adaptive 120s wrapper budget expired *after* the suite completed. A later run took 103s,
     confirming 120s is genuinely marginal. **Confirms the standing
     `adaptive-build-timeout-false-timeout` watch — promote from watch to plan-worthy.**
  2. **CodeRabbit red on all three HEADs** with no `run_id`, no log, no timestamps, while every
     required check was green — a bot-infrastructure signal, not a code finding.
  3. **Transient dirty state on `main` mid-run** (`extension-contract.md` modified, untracked
     `ext-point-domain-verb.md`) tripped the cache-sync staleness guard; cleared on re-check,
     **not from this plan** — most likely a concurrent editing session. Notably the guard
     *worked*: it caught foreign mutation rather than silently syncing over it.

## Routing and Merge Behavior

- **Review**: three iterations, each productive.
  - CodeRabbit — a genuinely self-contradictory sentence in the contract **this plan authored**
    (TASK-006), plus MD040 fences (TASK-005). A self-review pass that caught the plan's own new
    prose defect.
  - Gemini — a real internal inconsistency: the ext-point membership test did not filter `#`
    comments while the key-parse loop two lines below did (TASK-007). **Fourth consecutive
    landing where the sunset-flagged gemini produced a real finding** (cf. PLAN-20, PLAN-22).
  - One gemini finding **rejected on grounded evidence** (the `startswith('---')` idiom is the
    convention in the sibling analyzer) — correct disposition discipline: refuted with a reason,
    not silently dropped.
- **CI/merge**: all required checks green; merged via the queue; branch cleanup complete;
  worktree removed; `main` clean at `cd931fb63`.
- **Triage judgment call (operator-flagged, endorsed).** The recurring CodeRabbit red was
  triaged through a full envelope once, then the two identical recurrences resolved inline
  rather than re-spending ~150k tokens each. That is a deviation from the contract's default
  and the operator surfaced it explicitly. The judgment was sound — identical signal, already
  fully diagnosed — and the transparency is the right pattern. **Records as a watch**: a
  bot-infrastructure red that recurs across HEADs with no run_id has no cheap-recurrence path
  in the contract; the envelope cost is per-occurrence by default.
- **Surface collisions**: none. PLAN-28 ran concurrently with PLAN-24/25/26/30 and the predicted
  disjointness held — no rebase conflicts, no re-verify signals.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `962`, landing `landings/PLAN-28.md`)
- [x] epic.md queue row reconciled from status.json
- [x] Watch `adaptive-build-timeout-false-timeout` — **escalated** (now confirmed with hard
      numbers: 62.47s suite under a 120s budget, later run 103s)
- [x] Watch opened: recurring-bot-infrastructure-red has no cheap-recurrence triage path
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Adaptive build-timeout budget is marginal, not wrong-in-principle.** Two independent
  datapoints now (62.47s completed-then-timed-out; 103s later run against a 120s budget).
  This has outgrown watch status. Candidate for a staged spec — the fix is a budget derived
  from observed suite duration rather than a fixed adaptive ceiling.
- **Recurring bot-infrastructure red.** Consider a contract path for "identical bot-infra
  signal already triaged at a prior HEAD" so the ~150k envelope is not re-spent per recurrence.
  Fold into PLAN-31 or a future review-barrier plan rather than standing alone.
- **Marketplace/`.claude/` mirror.** D1/D2 edited `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`
  (project-local) while D3 edited the marketplace bundle. Worth confirming at the next
  housekeeping pass that the project-local step and any marketplace counterpart have not
  re-diverged — the mirror is exactly the surface this plan proved can drift silently.
