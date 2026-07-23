# Finalize Steps — Dispatched vs Inline Split

This document is the single source of truth for which of the default + project finalize steps **dispatch** (run under `Task: execution-context-{level}`) and which run **inline** (pure scripts or trivial orchestration in the main context). The phase-6-finalize `SKILL.md` § "Dispatched workflows vs inline steps" points here; the classification is consumed by the Execute Step Pipeline step's dispatch branch.

Every default + project finalize step registered in `marshal.json`'s `plan.phase-6-finalize.steps` is classified below as either dispatched or inline. Every dispatched step resolves under the phase-scoped registry — `manage-config effort resolve-target --phase phase-6-finalize [--role <subkey>]`.

## Closure invariant

Every step in the authoritative registry (`marshal.json` → `plan.phase-6-finalize.steps`) carries **exactly one** classification: it appears in either the dispatched roster or the inline roster, never both and never neither. Steps are named by their exact registry key (`default:` / `project:` / `bundle:skill` prefix included) so the rosters compare against the registry without normalisation.

Adding a new finalize step without classifying it here turns the guarding regression red. The invariant is pinned by `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`, which also asserts that no step-count claim is reintroduced into this document or into the `SKILL.md` § "Dispatched workflows vs inline steps" section — counts drift silently against a registry that grows, so the rosters are deliberately count-free.

## Dispatched steps

- `default:pre-submission-self-review` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`)
- `default:create-pr` — → `phase-6-finalize` (no `--role`)
- `default:lessons-capture` — → `phase-6-finalize --role post-run-review`
- `default:adr-propose` — → `phase-6-finalize --role post-run-review`; dispatcher-gated on the decision-shape Signal Gate
- `plan-marshall:automatic-review` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) — **FIND-only**: files its own `pr-comment` findings and marks done, taking no `producer` runtime input at all
- `default:sonar-roundtrip` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) — **FIND-only**: files its own `sonar-issue` findings and marks done, taking no `producer` runtime input at all
- `default:architecture-refresh` — hybrid, classified dispatched: its Tier 0 discover + diff is deterministic inline script work, and its Tier 1 re-enrichment fans out under `phase-6-finalize` per affected module — the only per-iteration parallel dispatch in the contract. The dispatching tier governs the classification, so the step carries exactly one roster row.
- `default:finalize-step-simplify` — → `phase-6-finalize` (no `--role`); holistic post-implementation simplification sweep whose edits settle onto HEAD before the push barrier
- `default:finalize-step-security-audit` — → `phase-6-finalize` (`persona: persona-security-expert`); hardening edits settle onto HEAD before the push barrier
- `project:finalize-step-plugin-doctor` — (meta-project only) → `phase-6-finalize --role verification-feedback` (`producer=plugin-doctor` runtime input)
- `project:finalize-step-lessons-housekeeping` — `mode: workflow`; reasons from the just-finished plan's outcome about the lessons corpus (remove / promote-then-retire / trim), so it earns an envelope
- `project:finalize-step-review-retrospective` — `mode: workflow`; hybrid by construction — a deterministic per-reviewer metrics pass augmented by an LLM qualitative judgment and comparative verdict
- `plan-marshall:plan-retrospective` — opt-in (`default_on: false`) → `phase-6-finalize --role post-run-review`; its LLM aspects iterate inside one envelope. It is the only roster entry that also accepts a forwarded `--session-id`.

`/workflow-pr-doctor` (a slash-command surface, not a registered finalize step) dispatches → `phase-6-finalize --role verification-feedback` (`producer=pr-state` runtime input). It carries no roster row because it is not in the registry.

**Dispatcher-owned unified triage (not a manifest step)**: after BOTH `plan-marshall:automatic-review` and `sonar-roundtrip` have filed, the phase-6-finalize dispatcher's Step 3 item 7c fires ONE additional dispatch — `phase-6-finalize --role verification-feedback` with `producer=finalize-feedback` — over the union of their pending `pr-comment` ∪ `sonar-issue` findings. This is the ONLY place `producer=finalize-feedback` triage happens in finalize. It carries no roster row of its own and produces no `phase_steps["6-finalize"]` record. See [`../SKILL.md`](../SKILL.md) Step 3 item 7c and [`../../plan-marshall/workflow/verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) § "Producer modes".

## Inline steps

The inline steps are pure scripts or trivial orchestration that earn no envelope:

- `default:finalize-step-sync-baseline` — early baseline rebase onto `origin/{base_branch}`
- `default:pre-push-quality-gate` — per-bundle `quality-gate` sweep plus the whole-tree module-tests divergence gate
- `default:push` — the single push barrier
- `default:ci-verify` — deterministic taxonomy-classification script (`scripts/ci_verify.py`)
- `default:branch-cleanup` — adapts to PR mode or local-only based on `create-pr` presence
- `default:finalize-step-preference-emitter` — deterministic within-plan disposition aggregation routed to `architecture enrich`
- `default:record-metrics` — record final plan metrics before archive
- `default:finalize-step-print-phase-breakdown` — capture the Phase Breakdown table from `metrics.md`
- `default:archive-plan` — archive the completed plan
- `project:finalize-step-era-stamp-fill` — `mode: script-executor`; resolves the `PR-PENDING` era-stamp sentinel to the real PR number and pushes the correction
- `project:finalize-step-deploy-target` — generate Claude Code target output via the multi-target generator
- `project:finalize-step-sync-plugin-cache` — synchronize the plugin cache from `target/claude/`

`default:ci-verify` deserves a note: its green pass-through (`final_status == success` AND no failing checks) marks the step done with ZERO dispatch, and only genuinely-red CI files one taxonomy finding per failing check and returns a per-producer needs-triage signal that the dispatcher routes to `verification-feedback` (the sole LLM step, red-CI only). This green-early-return / no-dispatch bypass is documented BEFORE the red-CI triage dispatch it bypasses.

CI completion is no longer a sibling step in this roster — it is a dispatcher-resolved precondition (`requires: [ci-complete]`) checked inline before any consumer step runs; see the SKILL.md Execute Step Pipeline step § "Precondition resolution".

For the rationale see [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 5 (find the LLM core, not the wrapping step).
