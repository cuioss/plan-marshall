# History: Process compliance — make rule-following structural, especially on opencode

slug: process-compliance
closed: 2026-10-07

> Frozen record of the epic at close. `epic.md`, the queue rows, the specs, the landings, the
> inbox and the logs stay in this tree untouched; this file is the summary a later reader
> starts from. Close freezes and never deletes.

## Closing rationale

Closed by operator instruction on 2026-10-07. plan-marshall's workflow machinery is being
rewritten as plan-marshall-mcp, which supersedes most of this epic's staged and parked work.
The work that still matters for plan-marshall itself — defects that block or mislead a normal
run today, and high-priority work on things the rewrite does not replace — was cut into the
successor epic `live-blockers` (`.plan/orchestrator/live-blockers/`). Everything else was
left where it stood.

## Vision as pursued

Across three shipped finalize-machinery plans, every run observed the same governing
pattern: prevention failed everywhere, detection-and-correction worked everywhere.
Agents rationalized around prose rules (five simultaneously in force), fell back to
improvisation wherever the compliant path did not cover the use case, and needed
repeated nudges for invariants already recorded as active corrections — worst on the
opencode target, where Claude affordances (session identity, transcripts, hooks) do
not exist and the abstraction leaks them as hard blocks. This epic moves each guard
from the boundary where the damage is already done to the earliest point where the
deviation is decidable, so rule-following is structural rather than disciplinary.
Too large for one plan: it spans transition gates, worktree machinery, generator and
wrapper contracts, dispatch registries, persona behavior rules, and opencode-specific
abstraction repairs. Done looks like a run that cannot skip phases, cannot dirty
main, cannot invent invocations, and cannot strand on missing Claude concepts —
with every remaining gap a logged, visible exemption rather than a silent slip.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: Process compliance: make rule-following structural, especially on opencode

#### START HERE

**Resume anchor**: 2026-10-02 NEXT gate-checked: 0 of 2 slots emitted. Prep-ready passes corpus-wide, blocking_count 0. Disjoint fails closed: comparison indeterminate plus 100-plus sibling overlaps per staged spec. Nothing launched. Next: operator decides override-emit in queue order, narrow scope, or close epic. 1 inbox message still queued on archive_conflict.
**Phase**: orchestrating
**Parked**:
- PLAN-08 (WS-03)
- PLAN-09 (WS-03)
- PLAN-11 (WS-06)
- PLAN-14 (WS-04)
**Queue** (staged, in order):
1. PLAN-10 (WS-01)
2. PLAN-16 (WS-01)
3. PLAN-17 (WS-01)
4. PLAN-18 (WS-01)
5. PLAN-21 (WS-07)
6. PLAN-22 (WS-03)
7. PLAN-23 (WS-07)
8. PLAN-26 (WS-02)
9. PLAN-27 (WS-05)
- PLAN-01 (WS-01) — plan=phase-gates — PR 1540 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-02) — plan=plan-02-worktree-discipline — PR 1547 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-03) — plan=compliant-paths — PR 1542 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-04) — plan=plan-04-persona-behavior — PR 1556 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-05) — plan=implement-dispatch-envelopes-process-compliance — PR 1583 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-05) — plan=plan-06-dispatch-roster — PR 1606 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-06) — plan=plan-07-opencode-repairs — PR 1554 — landing=landings/PLAN-07.md — status: shipped
- PLAN-12 (WS-05) — plan=plan-12-tool-triage — PR 1654 — landing=landings/PLAN-12.md — status: shipped
- PLAN-13 (WS-07) — plan=plan-13-finalize-mechanism-defects — PR 1651 — landing=landings/PLAN-13.md — status: shipped
- PLAN-15 (WS-06) — plan=implement-opencode-enforcement-parity — PR 1618 — landing=landings/PLAN-15.md — status: shipped
- PLAN-19 (WS-05) — status: transferred
- PLAN-20 (WS-07) — status: transferred
- PLAN-24 (WS-07) — status: transferred
- PLAN-25 (WS-05) — status: transferred

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-08 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/tools-integration-ci/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/ |
| 2 | PLAN-09 | WS-03 | parked | AGENTS.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/ |
| 3 | PLAN-10 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-config/scripts/; marketplace/bundles/plan-marshall/skills/manage-plan-documents/scripts/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-1-init/; marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md; marketplace/bundles/plan-marshall/skills/plan-marshall/; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py; test/plan-marshall/manage-config/; test/plan-marshall/manage-plan-documents/; test/plan-marshall/manage-status/; test/plan-marshall/plan-marshall/; test/plan-marshall/plan-orchestrator/ |
| 4 | PLAN-11 | WS-06 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/phase-5-execute/; test/plan-marshall/plan-orchestrator/ |
| 5 | PLAN-14 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/; test/plan-marshall/persona-plan-marshall-agent/ |
| 6 | PLAN-16 | WS-01 | staged | CLAUDE.md; marketplace/bundles/plan-marshall/agents/execution-context.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/; marketplace/bundles/plan-marshall/skills/phase-1-init/; marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md; test/plan-marshall/manage-config/; test/plan-marshall/manage-execution-manifest/; test/plan-marshall/manage-status/ |
| 7 | PLAN-17 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/_plan_state_exemption.py; marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/workflow/inventory.md; test/plan-marshall/plan-marshall/; test/plan-marshall/script-shared/ |
| 8 | PLAN-18 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/; marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md; marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/standards/change-types.md; test/plan-marshall/manage-solution-outline/; test/plan-marshall/plan-marshall/; test/plan-marshall/plan-marshall/test_transition_refusal_halt_call_sites.py |
| 9 | PLAN-21 | WS-07 | staged | .claude/skills/finalize-step-lessons-housekeeping/; .claude/skills/finalize-step-plugin-doctor/; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/execution-context-dispatch-audit.md; test/plan-marshall/manage-metrics/; test/plan-marshall/manage-references/; test/plan-marshall/manage-status/; test/plan-marshall/phase-6-finalize/; test/plan-marshall/plan-retrospective/ |
| 10 | PLAN-22 | WS-03 | staged | .claude/skills/; .github/; doc/user/efforts.adoc; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-build.md; marketplace/bundles/plan-marshall/skills/manage-lessons/; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py; marketplace/bundles/plan-marshall/skills/manage-logging/scripts/manage-logging.py; marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/_cmd_cleanup.py; marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/artifact-consistency.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-plan-artifacts.py; test/plan-marshall/audit-archived-plan-retrospectives/; test/plan-marshall/manage-ci-artifacts/; test/plan-marshall/manage-files/; test/plan-marshall/manage-findings/; test/plan-marshall/manage-logging/; test/plan-marshall/manage-metrics/; test/plan-marshall/manage-references/; test/plan-marshall/manage-status/; test/plan-marshall/plan-retrospective/; test/plan-marshall/tools-file-ops/ |
| 11 | PLAN-23 | WS-07 | staged | build.py; marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/; marketplace/bundles/plan-marshall/skills/build-server-client/; marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py; pyproject.toml; test/plan-marshall/manage-tasks/; test/plan-marshall/phase-6-finalize/ |
| 12 | PLAN-26 | WS-02 | staged | marketplace/bundles/plan-marshall/skills/manage-locks/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/orchestrator_worktree.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py; test/plan-marshall/manage-locks/; test/plan-marshall/plan-orchestrator/; test/plan-marshall/workflow-integration-git/ |
| 13 | PLAN-27 | WS-05 | staged | marketplace/bundles/plan-marshall/agents/execution-context-reader.md; marketplace/bundles/plan-marshall/agents/execution-context.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; test/plan-marshall/manage-findings/; test/plan-marshall/phase-5-execute/ |

## Queue outcome

27 plans: 10 shipped, 4 closed unshipped, 4 parked, 9 at another status.

### Shipped

| Plan | Slug | Status | PR |
|---|---|---|---|
| PLAN-01 | phase-gates | shipped | 1540 |
| PLAN-02 | worktree-discipline | shipped | 1547 |
| PLAN-03 | compliant-paths | shipped | 1542 |
| PLAN-04 | persona-behavior | shipped | 1556 |
| PLAN-05 | dispatch-envelopes | shipped | 1583 |
| PLAN-06 | dispatch-roster | shipped | 1606 |
| PLAN-07 | opencode-repairs | shipped | 1554 |
| PLAN-12 | tool-triage | shipped | 1654 |
| PLAN-13 | finalize-mechanism-defects | shipped | 1651 |
| PLAN-15 | opencode-enforcement-parity | shipped | 1618 |

### Closed unshipped

| Plan | Slug | Status |
|---|---|---|
| PLAN-19 | execute-verification-loop | transferred |
| PLAN-20 | self-review-convergence | transferred |
| PLAN-24 | review-and-pr-record-integrity | transferred |
| PLAN-25 | build-routing-integrity | transferred |

### Parked at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-08 | process-contracts | parked |
| PLAN-09 | store-access | parked |
| PLAN-11 | landing-facts | parked |
| PLAN-14 | persona-conduct-lessons | parked |

### Other status at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-10 | entry-capture | staged |
| PLAN-16 | init-lane-fidelity | staged |
| PLAN-17 | concurrent-plan-isolation | staged |
| PLAN-18 | outline-lane-contracts | staged |
| PLAN-21 | finalize-step-accounting | staged |
| PLAN-22 | runtime-state-path-migration | staged |
| PLAN-23 | push-boundary-evidence | staged |
| PLAN-26 | git-and-worktree-contracts | staged |
| PLAN-27 | execute-guards-and-dispatch-header | staged |

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- `PLAN-19` → `PLAN-LB-06`, `PLAN-20` → `PLAN-LB-02`, `PLAN-24` → `PLAN-LB-18` / `PLAN-LB-19`, `PLAN-25` → `PLAN-LB-12` (rows `transferred`).
- `PLAN-23` D3 → `PLAN-LB-01`, D4 → `PLAN-LB-05`; its D1/D2 are in `backlog.md` § 2.8.
- `PLAN-27` D1 → `PLAN-LB-07`; its D2 (dispatch header) is in `backlog.md` § 1.20.
- `PLAN-21` D2 → `PLAN-LB-10`; the rest is in `backlog.md` §§ 1.13 and 1.20.
- `PLAN-10` D1 → `PLAN-LB-04`.
- Open defect "footprint gate treats `.plan/marshal.json` as docs-only" → `PLAN-LB-16`; "installed skill copy carries no workflow documents" → `PLAN-LB-17`.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (27 entries) and § Watches (8 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- `PLAN-16`, `PLAN-17`, `PLAN-18`, `PLAN-22` and `PLAN-26` are ready specs ranked medium; see `backlog.md` §§ 1.15, 1.18, 1.19, 1.24 and 4.10.

### Inbox messages undrained at close

- `inbox/opencode-bootstrap-executor-fix-003.md`

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
