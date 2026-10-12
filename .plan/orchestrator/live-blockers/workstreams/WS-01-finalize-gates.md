# WS-01: Finalize and Phase Gates

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-finalize-gates.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Gates and steps in the plan lifecycle that block a correct run, report a false result or cannot proceed without an operator override. The workstream closes when a plan can pass refine, execute and finalize without `--force`, `--override` or a hand-set field.

## Scope

- In scope: the phase handshake, the pre-push and freshness gates, pre-submission self-review, triage and fix tasks, the scope-creep guard, the findings store, archive and merge gating, finalize step records, commit staging
- Out of scope: build execution and Maven parsing (WS-02); the orchestrator launch gate (WS-03); harness sync and CI (WS-04); review-bot behaviour (WS-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-22-finalize-loop-control | staged | Retried steps record their outcome; loop-backs budgeted per source; self-review can be closed; a live CI run is not a timeout |
| PLAN-LB-25-phase-and-merge-gates | staged | Findings gate holds at archive and merge; merge waits without sleep; light-lane refine boundary |
| PLAN-LB-26-execute-loop-triage | staged | Fix tasks get scheduled; triage survives a re-check; one wait rule for long builds |
| PLAN-LB-27-plan-footprint | staged | Staging allowlist; scope-creep guard measures the plan's own changes |
| PLAN-LB-32-head-dependent-step-refire | staged | High priority. A re-fired project step re-examines only what the fix commit could have changed |
| PLAN-LB-34-self-review-surfacing-foundation-and-java | staged | Top priority. Several self-review surfacers coexist and are merged; uncovered files are reported as not covered; first second surfacer, for Java. Takes PLAN-LB-03's deliverables from PLAN-LB-28 |
| PLAN-LB-35-self-review-javascript-and-python | staged | Surfacers for JavaScript/TypeScript and consumer Python. Waits for PLAN-LB-34 |
| PLAN-LB-36-self-review-documents-containers-requirements | staged | Surfacers for documents, containers and requirements; the outcome for files no domain claims. Waits for PLAN-LB-34 |
| PLAN-LB-02-self-review-convergence | superseded | PLAN-LB-22 (all deliverables) |
| PLAN-LB-04-light-lane-refine-boundary | superseded | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05-unrunnable-waits | superseded | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06-triage-fix-task-loop | superseded | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07-scope-creep-guard | superseded | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08-triage-survives-recheck | superseded | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09-pending-findings-gate | superseded | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10-retried-step-outcome | superseded | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11-finalize-staging-allowlist | superseded | PLAN-LB-27 (all deliverables) |
| PLAN-LB-01-push-freshness-gate | superseded | PLAN-LB-23 (all deliverables) |
| PLAN-LB-03-self-review-consumer-repos | superseded | PLAN-LB-28 (all deliverables) |

## Sequencing and Surface Notes

- PLAN-LB-22 is the hub: it shares `phase-6-finalize/SKILL.md`, `manage-status` or `execution.md` with every other plan of this workstream. Run it first, beside a plan of another workstream.
- PLAN-LB-25 and PLAN-LB-26 share no file and may run together.
- PLAN-LB-27 shares `phase-5-execute/SKILL.md` and `execution.md` with PLAN-LB-26 and `phase-6-finalize/SKILL.md` with PLAN-LB-25; run it after both, beside PLAN-LB-28.
- PLAN-LB-32 runs ahead of PLAN-LB-25 to PLAN-LB-27. It shares only `phase-6-finalize/SKILL.md` with PLAN-LB-24, PLAN-LB-25 and PLAN-LB-27, and `ext-point-finalize-step.md` with PLAN-LB-27.
- PLAN-LB-34 heads a chain: PLAN-LB-35 and PLAN-LB-36 start only after it has landed, and may then run together. PLAN-LB-34 shares `pre-submission-self-review.md` with PLAN-LB-26; sequence those two.
- PLAN-LB-01 and PLAN-LB-03 left this workstream at the regrouping: they were absorbed by PLAN-LB-23 and PLAN-LB-28 in WS-02.
