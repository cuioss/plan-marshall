envelope_version=1
sender_type=plan
sender_id=plan-06-dispatch-roster
epic=process-compliance
kind=finding
created=2026-09-24T10:24:37Z

# Finding: sync-plugin-cache on-main executor regen targets claude on opencode sessions

plan: plan-06-dispatch-roster (epic process-compliance, PLAN-06)
kind: finding
phase: 6-finalize (project:finalize-step-sync-plugin-cache, Step 3)

## Observation

The step's documented regen invocation (`generate_executor generate`, no flags)
auto-detected context `/home/oliver/.config/opencode/skills`, registered 0
marketplace scripts (160 local), and emitted `Target: claude` onto main's
`.plan/execute-script.py` — breaking every subsequent executor call from main
(`ModuleNotFoundError: No module named 'plan_logging'`).

Recovery (operator-visible, completed): direct
`generate_executor.py generate --marketplace-root /home/oliver/git/plan-marshall --target opencode`
→ 319 scripts, opencode target, executor verified working via `mark-step-done`.

## Why this matters

- The regen step is the single project-level owner of on-main executor
  regeneration; its documented invocation is target-blind on a multi-target
  checkout. On any non-claude session it breaks the executor it was meant to
  refresh — the exact file the rest of finalize keeps calling.
- The failure is silent until the next executor call; the step reported success.

## Proposed disposition (orchestrator decides)

- Thread `--target` (from the live runtime target) and `--marketplace-root`
  through the step's regen invocation, or resolve both inside the verb.
- Until then, opencode finalize runs must use the direct invocation above.

No repository source touched for this filing; recorded per the standing
emit-convention instruction.
