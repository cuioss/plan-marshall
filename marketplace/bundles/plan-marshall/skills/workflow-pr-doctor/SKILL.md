---
name: workflow-pr-doctor
description: Diagnose and fix PR issues (build, reviews, Sonar) — thin wrapper around verification-feedback with producer=pr-state
user-invocable: true
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# PR Doctor Skill — Redirect

The pr-doctor body (CI wait, multi-source fetch over build / PR comments / Sonar, per-finding triage) lives in [`plan-marshall:plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md) § Step 1 under `producer=pr-state`. The triage core (FIX / SUPPRESS / ACCEPT / AskUserQuestion) lives in [`plan-marshall:plan-marshall/workflow/triage.md`](../plan-marshall/workflow/triage.md) Steps 1-6.

## Enforcement

**Execution mode**: Dispatch `verification-feedback.md` with `producer=pr-state`; do not implement the body here.

**Prohibited actions:**
- Do not duplicate the pr-state body in this file — `verification-feedback.md` is the single source of truth.
- Do not invoke this skill directly from manifest steps — the `phase-6-finalize` finalize loop dispatches `verification-feedback` directly.

**Constraints:**
- The slash-command surface (`/workflow-pr-doctor`) MUST resolve through `manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback` and dispatch the canonical executor variant.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Dispatch

When `/workflow-pr-doctor` is invoked, resolve the level + target via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize --role verification-feedback \
  --workflow plan-marshall:plan-marshall/workflow/verification-feedback.md --plan-id {plan_id} \
  --caller plan-marshall:workflow-pr-doctor
```

The resolve carries the dispatch context (`--workflow`/`--plan-id`/`--caller`), so the seam emits the standardized `[DISPATCH]` work-log line and its paired decision-log record itself — see [`dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract. Do NOT hand-write a separate `[DISPATCH]` line; every firing re-runs the resolve, so the record is re-emitted per firing.

**On a standalone run** — this skill's `plan_id` is documented below as "unset for standalone runs" — pass `--plan-id none` rather than interpolating an empty `{plan_id}`. The flag is optional and the resolver accepts the literal `none`, routing the seam emission to the global log instead of a plan work-log; `--plan-id` with an empty value is not the same thing and is not a supported form.

Then dispatch the returned `target` (`execution-context-{level}` or canonical) with this prompt body:

```yaml
name: workflow-pr-doctor
plan_id: {plan_id}                # current plan or unset for standalone runs
workflow: plan-marshall:plan-marshall/workflow/verification-feedback
skills:
  - plan-marshall:manage-findings
  - plan-marshall:manage-tasks
  - plan-marshall:manage-architecture
  - plan-marshall:manage-config
  - plan-marshall:tools-integration-ci
  - plan-marshall:workflow-integration-git
  - plan-marshall:workflow-integration-github
  - plan-marshall:workflow-integration-sonar
WORKTREE: {worktree}
producer: pr-state
pr_number: {pr_number}            # required; auto-detect via `ci pr view` when absent
caller_phase: phase-6-finalize
```

The dispatched envelope runs `verification-feedback.md` Step 1 (`producer=pr-state` branch) inline and continues into the triage core.

## Output

Pass-through from `verification-feedback.md`:

```toon
status: success | loop_back | error | ci_failure
display_detail: "<≤80 char summary, e.g. 'PR #123 diagnosed, 2 issues, 1 fix applied'>"
producer: pr-state
findings_processed: {N}
findings_resolved: {M}
fix_tasks_created: {K}
```

## Canonical invocations

The canonical argparse surface for `pr_doctor.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### track-attempt

```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor track-attempt \
  --category {build,reviews,sonar} --current CURRENT [--max-attempts MAX_ATTEMPTS]
```

### diagnose

```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor diagnose \
  [--build-status {success,failure}] [--build-failures BUILD_FAILURES] \
  [--review-comments REVIEW_COMMENTS] [--sonar-issues SONAR_ISSUES]
```

### parse-handoff

```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor parse-handoff \
  --handoff HANDOFF [--pr PR] [--checks {build,reviews,sonar,all}] \
  [--auto-fix] [--wait] [--no-wait] [--max-fix-attempts MAX_FIX_ATTEMPTS]
```

## Related

- [`verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md) — orchestrator body.
- [`triage.md`](../plan-marshall/workflow/triage.md) — canonical per-finding decision + action loop.
- [`standards/automated-review-lifecycle.md`](standards/automated-review-lifecycle.md) — phase-6-finalize automated-review variant (now a thin sibling of `producer=pr-comment` in `verification-feedback.md`).
