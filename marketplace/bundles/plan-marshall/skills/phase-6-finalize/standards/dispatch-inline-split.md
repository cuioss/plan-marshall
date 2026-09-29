# Finalize Steps — Dispatched vs Inline Split

This document is the single source of truth for which of the default + project finalize steps **dispatch** (run under `Task: execution-context-{level}`) and which run **inline** (pure scripts or trivial orchestration in the main context). The phase-6-finalize `SKILL.md` § "Dispatched workflows vs inline steps" points here; the classification is consumed by the Execute Step Pipeline step's dispatch branch.

Every default + project finalize step registered in `marshal.json`'s `plan.phase-6-finalize.steps` is classified below as either dispatched or inline. Every dispatched step resolves under the phase-scoped registry — `manage-config effort resolve-target --phase phase-6-finalize [--role <subkey>]`.

## Closure invariant

Every step in the authoritative registry (`marshal.json` → `plan.phase-6-finalize.steps`) carries **exactly one** classification: it appears in either the dispatched roster or the inline roster, never both and never neither. Steps are named by their exact registry key (`default:` / `project:` / `bundle:skill` prefix included) so the rosters compare against the registry without normalisation.

Adding a new finalize step without classifying it here turns the guarding regression red. The invariant is pinned by `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`, which also asserts that no step-count claim is reintroduced into this document or into the `SKILL.md` § "Dispatched workflows vs inline steps" section — counts drift silently against a registry that grows, so the rosters are deliberately count-free.

## Dispatched steps

**Resolver-lookup completeness invariant**: every row below declares the `manage-config effort resolve-target` lookup it resolves under — the `--phase` value plus the `--role` sub-key, or an explicit "no `--role`" when the step tracks `phase-6-finalize.default`. A row without a declared lookup leaves the dispatcher to guess the sub-key at dispatch time, so the column is complete by construction rather than as-needed. This is a completeness obligation on the roster, stated here as an invariant in its own right; it is **not** an explanation for any past missed `[DISPATCH]` emission — the emission rides the `effort resolve-target` **resolve seam** (a per-firing side effect of the resolve each dispatch performs; see [`../SKILL.md`](../SKILL.md) Step 3 and [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md)), and the two concerns are independent.

**`--role post-run-review` is a DERIVED value, not a roster decision.** A row carries that sub-key iff the step's own authoritative doc declares `post_run_review: true`; the rows below record the derived outcome so the roster stays complete, but the frontmatter fact is the source. Changing a step's `post_run_review` declaration changes its lookup here — see [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter".

**Explicit per-step skills column**: every row below carries its full prompt skill set as `skills:` — the skills the dispatched envelope loads. Producer rows use the D1 producer vocabulary (`producer=plugin-doctor`, `producer=pr-state`, `producer=finalize-feedback`).

- `default:pre-submission-self-review` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`); skills: `plan-marshall:persona-plan-marshall-agent`, `pm-plugin-development:plugin-architecture`
- `default:create-pr` — → `phase-6-finalize` (no `--role`); skills: `plan-marshall:tools-integration-ci`, `plan-marshall:workflow-integration-git`
- `default:lessons-capture` — → `phase-6-finalize --role post-run-review` (derived — declares `post_run_review: true`); skills: `plan-marshall:manage-lessons`, `plan-marshall:persona-plan-marshall-agent`
- `default:adr-propose` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default` — it looks back at plan history but its inputs are settled before the merge gate, so it is not a `post_run_review` member); dispatcher-gated on the decision-shape Signal Gate; skills: `plan-marshall:manage-adr`, `plan-marshall:persona-plan-marshall-agent`
- `plan-marshall:automatic-review` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) — **FIND-only**: files its own `pr-comment` findings and marks done, taking no `producer` runtime input at all; skills: `plan-marshall:workflow-integration-github`, `plan-marshall:manage-findings`
- `default:sonar-roundtrip` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) — **FIND-only**: files its own `sonar-issue` findings and marks done, taking no `producer` runtime input at all; skills: `plan-marshall:workflow-integration-sonar`, `plan-marshall:manage-findings`
- `default:finalize-step-simplify` — → `phase-6-finalize` (no `--role`); holistic post-implementation simplification sweep whose edits settle onto HEAD before the push barrier; skills: `plan-marshall:persona-plan-marshall-agent`, `plan-marshall:ref-code-quality`
- `default:finalize-step-security-audit` — → `phase-6-finalize` (`persona: persona-security-expert`); hardening edits settle onto HEAD before the push barrier; skills: `plan-marshall:persona-security-expert`
- `project:finalize-step-plugin-doctor` — (meta-project only) → `phase-6-finalize --role verification-feedback` (`producer=plugin-doctor` runtime input); skills: `pm-plugin-development:plugin-doctor`, `pm-plugin-development:tools-marketplace-inventory`
- `project:finalize-step-lessons-housekeeping` — → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`); `mode: workflow`; reasons from the just-finished plan's outcome about the lessons corpus (remove / promote-then-retire / trim), so it earns an envelope; skills: `plan-marshall:manage-lessons`
- `project:finalize-step-review-retrospective` — → `phase-6-finalize --role post-run-review` (derived — declares `post_run_review: true`); `mode: workflow`; hybrid by construction — a deterministic per-reviewer metrics pass augmented by an LLM qualitative judgment and comparative verdict; skills: `plan-marshall:manage-findings`, `plan-marshall:manage-metrics`
- `plan-marshall:plan-retrospective` — opt-in (`default_on: false`) → `phase-6-finalize --role post-run-review` (derived — declares `post_run_review: true`); its LLM aspects iterate inside one envelope. It is the only roster entry that also accepts a forwarded `--session-id`. Completion guard: record-before-return — the body lands `mark-step-done` before composing its return TOON; skills: `plan-marshall:manage-metrics`, `plan-marshall:manage-lessons`

`/workflow-pr-doctor` (a slash-command surface, not a registered finalize step) dispatches → `phase-6-finalize --role verification-feedback` (`producer=pr-state` runtime input). It carries no roster row because it is not in the registry.

**Dispatcher-owned unified triage (not a manifest step)**: after BOTH `plan-marshall:automatic-review` and `sonar-roundtrip` have filed, the phase-6-finalize dispatcher's Step 3 item 7c fires ONE additional dispatch — `phase-6-finalize --role verification-feedback` with `producer=finalize-feedback` — over the union of their pending `pr-comment` ∪ `sonar-issue` findings. This is the ONLY place `producer=finalize-feedback` triage happens in finalize. It carries no roster row of its own and produces no `phase_steps["6-finalize"]` record. See [`../SKILL.md`](../SKILL.md) Step 3 item 7c and [`../../plan-marshall/workflow/verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) § "Producer modes".

## Inline steps

The inline steps are pure scripts or trivial orchestration that earn no envelope:

- `default:finalize-step-sync-baseline` — early baseline rebase onto `origin/{base_branch}`
- `default:pre-push-quality-gate` — per-bundle `quality-gate` sweep plus the whole-tree module-tests divergence gate
- `default:architecture-refresh` — its Tier-1 `prompt` mode requires an `AskUserQuestion`, which a dispatched leaf cannot fire
- `default:push` — the single push barrier
- `default:ci-verify` — deterministic taxonomy-classification script (`scripts/ci_verify.py`)
- `default:branch-cleanup` — adapts to PR mode or local-only based on `create-pr` presence
- `default:finalize-step-preference-emitter` — deterministic within-plan disposition aggregation whose owed `architecture enrich` hints are filed as a follow-up record (post-merge-ordered, so it never calls `enrich` itself)
- `default:record-metrics` — record final plan metrics before archive
- `default:finalize-step-print-phase-breakdown` — capture the Phase Breakdown table from `metrics.md`
- `default:emit-landing` — terminal machine-readable emission; assembles the run's already-recorded facts into the `kind: landing` inbox message the epic drains and writes it via `orchestrator inbox write`, taking no reasoning of its own
- `default:archive-plan` — archive the completed plan
- `project:finalize-step-era-stamp-fill` — `mode: script-executor`; resolves the `PR-PENDING` era-stamp sentinel to the real PR number and pushes the correction
- `project:finalize-step-deploy-target` — generate Claude Code target output via the multi-target generator
- `project:finalize-step-sync-plugin-cache` — synchronize the plugin cache from `target/claude/`

`default:ci-verify` deserves a note: its green pass-through (`final_status == success` AND no failing checks) marks the step done with ZERO dispatch, and only genuinely-red CI files one taxonomy finding per failing check and returns a per-producer needs-triage signal that the dispatcher routes to `verification-feedback` (the sole LLM step, red-CI only). This green-early-return / no-dispatch bypass is documented BEFORE the red-CI triage dispatch it bypasses.

CI completion is no longer a sibling step in this roster — it is a dispatcher-resolved precondition (`requires: [ci-complete]`) checked inline before any consumer step runs; see the SKILL.md Execute Step Pipeline step § "Precondition resolution".

For the rationale see [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 5 (find the LLM core, not the wrapping step).

## A forked subagent must not run `default:branch-cleanup`

`default:branch-cleanup` — and therefore the finalize pipeline that reaches it — runs in the **main context**, whose cwd the orchestrator can return to `{main_checkout}` before the worktree is removed. It never runs inside a forked subagent: an `execution-context-{level}` dispatch or any other spawned envelope. This is a constraint on where the whole pipeline runs, not only on how this one step is classified in the inline roster above — a finalize run forked into a subagent reaches this step with no way to complete it, for the reasons below.

- **The fork's cwd is pinned inside the worktree.** Under the cwd-pinned model (ADR-002), phase-5-execute entry pins the orchestrator's cwd to the plan's worktree root, and a subagent spawned from that context inherits it. A finalize run inside the fork therefore starts with its cwd inside the very directory `branch-cleanup` removes, and it has no way to re-anchor that cwd onto `{main_checkout}`. See [`cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md).
- **No re-anchor seam is constructible inside a subagent.** A subagent's Bash cwd resets to the inherited directory on every call, so a standalone `cd {main_checkout}` does not survive into the call that follows it. The forms that would carry a directory change into the removal call are both forbidden: `cd {path} && …` is two commands in one call, which the [one-command-per-call rule](../../persona-plan-marshall-agent/SKILL.md#bash-one-command-per-call) prohibits, and `env -C {path} …` is excluded by the same Bash discipline. The fork has no sanctioned way to stand outside the worktree when the removal runs.
- **The removal refuses, and `--force` does not override it.** `worktree-remove` refuses with `error: cwd_inside_removal_target` whenever the process cwd is the removal target or any directory beneath it, and `--force` does not lift that refusal. Its remedy — change directory out of the worktree and re-run — is exactly the move the previous point shows a fork cannot make, so `branch-cleanup` cannot complete from there. The refusal contract is owned by [`branch-cleanup.md`](branch-cleanup.md) § "Worktree Awareness"; it is not restated here.
