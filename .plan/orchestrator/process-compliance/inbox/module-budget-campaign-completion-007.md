envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T13:56:00Z
revision=1

# Process-rule issue: `mark-step-done` refuses the documented `failed` write on a re-fired step, so "a red gate aborts before push" is structurally unreachable on re-entry

Reporter: plan `module-budget-campaign-completion`, `project:finalize-step-plugin-doctor` dispatch.

## Observation

The plugin-doctor finalize step is `head_dependent: true`. A HEAD advance re-fires it
(item 1 of the finalize pipeline consults `verdict_currency classify`, which returned
`invalidated` on this run). On that re-fire the gate went **red**, and the step's own
documented failure path is:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor \
  --outcome failed --display-detail "plugin-doctor: {total_issues} violations"
```

That call is **refused**:

```
status: error
error: conflict
existing_outcome: done
requested_outcome: failed
message: "Step 'project:finalize-step-plugin-doctor' in phase '6-finalize' already marked
          as 'done'; use --force to overwrite with 'failed'"
```

The step's whole contract on a red gate is "record `failed`, then abort finalize **before**
`default:commit-push`". The refusal leaves the record asserting `done` — a green verdict for
a gate that is red — which is precisely the false-green the step exists to prevent. Only the
dispatcher noticing the mismatch (this run) or an operator re-entry rescues it; nothing in
the step's own sequence does.

The write succeeds with `--force`, which is the documented override for exactly this
("`--force` governs outcome conflicts"). This run used it and the record now reads `failed`.

## Siblings — every terminal-`failed` path written by a RE-FIRED step omits `--force`

The conflict guard is generic (`_cmd_mark_step.py`: `if existing_outcome != outcome and not
args.force`). Every documented caller that can land on a step carrying a stale non-terminal-
matching record is affected. Enumerated, all must be closed together:

1. `project:finalize-step-plugin-doctor` § Step 5 violation path — the observed failure.
2. `phase-6-finalize/SKILL.md` item 5d(c)/5d guard path — the dispatcher records
   `outcome: failed` on a step whose record is absent or terminal; absent is safe, but a
   re-fired `done` step that then reports a missing record is not.
3. `phase-6-finalize/SKILL.md` item 5 timeout path — `mark-step-done … --outcome failed
   "timed out after {budget}s"` on a re-fired step with a prior `done`.
4. `phase-6-finalize:ci_complete_precondition` consumer mapping — the `wait_failed` rows
   mark `outcome: failed` with `error: ci_failure (precondition)`, again on a step whose
   prior record may be `done` (a HEAD advance invalidates its precondition cache, so
   re-entry is the normal path there, not the exception).

## Consequence if unfixed

- A red structural gate silently reads as a passing step on every finalize re-entry.
- The `phase_steps_complete` handshake is satisfied by the stale `done`, so the phase
  transition is not blocked either — the failure has no downstream guard.

## Evidence

- Refusal: the `project:finalize-step-plugin-doctor` dispatch at 2026-09-25T13:52Z,
  `record_error: conflict`, returned by the leaf verbatim in its terminal payload.
- Guard source: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py:651`.
- Remediation applied this run: the same call with `--force` → `status: success`,
  `previous_outcome: done`, `outcome: failed`.
