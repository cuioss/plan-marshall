# PLAN-07: steward-wizard-config-integrity

epic: plan-optimization
workstream: WS-03

> Staged plan spec — one shippable unit, ready for `/plan-marshall` hand-off. Both deliverables
> below were reported by a consumer (cui-open-rewrite) during a first-run `/marshall-steward` wizard
> and **INDEPENDENTLY VERIFIED against upstream source by the orchestrator, 2026-07-18** — these are
> confirmed defects, not unverified leads. Re-ground the file:line citations at outline (they will
> drift).

## Objective

Close two manage-config / marshall-steward correctness gaps that a fresh-consumer wizard run
exposed: (1) `manage-config project set` silently accepts unknown field names, returning
`status: success` while writing dead keys that mask operator/doc errors; (2) the first-run wizard
leaves the core phase-6-finalize steps without explicit lanes, contradicting the documented
"fully explicit" intent. Both make fresh-project onboarding quietly wrong.

## Deliverables

### D1 — `project set` must reject unknown field names (Bug 1, severity: medium — silent data corruption)

**Verified (orchestrator, 2026-07-18):** `_cmd_system_plan.py` `cmd_project()` `set` branch validates
*values* for the known fields (`working_prefixes` shape at `:126-135`, `pr_strategy` at `:141-145`,
`pr_compact_max_changed_files` at `:146-150`) but has **no field-NAME whitelist**. Line `:152`
`project_config[field] = value` writes any `--field` unconditionally, then `success_exit` (`:155`).
An unknown field falls through `else: value = _coerce_value(args.value)` (`:137`) and persists with
`status: success`. Valid project fields are exactly the `DEFAULT_PROJECT` keys
(`_config_defaults.py:123-128`): `default_base_branch`, `working_prefixes`, `pr_strategy`,
`pr_compact_max_changed_files`.

**How it bit the consumer:** merge-queue opt-in was written to `project.use_merge_queue` (a dead
key nothing reads) instead of the real step-owned knob
`plan.phase-6-finalize.steps."default:branch-cleanup".use_merge_queue` (see
`marshall-steward/references/merge-queue-setup.md` § MQ-2). The green `status: success` actively hid
the mistake — the GitHub queue got enabled but finalize would not route through it.

**Reporter's suggested fix (confirm at outline):** in the `set` branch, reject any `field` not in the
`DEFAULT_PROJECT` key set with `error_exit(..., error_type='unknown_field')`, mirroring the existing
value-level validation. Unknown-field writes must never return `status: success`. **Acceptance:**
`project set --field use_merge_queue --value true` returns `status: error` / `unknown_field`; the four
known fields still set successfully; add a regression test.

### D2 — first-run wizard must materialize explicit finalize lanes (Bug 2, severity: low/medium — completeness gap)

**Verified (orchestrator, 2026-07-18):** `_materialize_finalize_lanes` (`_cmd_sync_defaults.py:317`)
is called ONLY from `cmd_sync_defaults` (`:447`). The first-run wizard never calls `sync-defaults`:
wizard-flow Step 16 (`wizard-flow.md:596,611`) runs only `steps-sort`, and `:318` explicitly notes
the first-run wizard does not invoke sync-defaults. So after a fresh wizard, only the two ask-tier
steps (`automatic-review`, `sonar-roundtrip`, set by Step 11b) carry a `lane`; the seven core steps
(`push`, `create-pr`, `ci-verify`, `lessons-capture`, `branch-cleanup`, `record-metrics`,
`archive-plan`) are lane-less — contradicting the "fully explicit" intent. The lane pass is reached
only on a later menu-mode run via SKILL.md "Re-Run Remediation Pass" step (e).

**Reporter's suggested fix (confirm at outline):** have the first-run wizard run `sync-defaults` (or
invoke the lane-materialization pass directly) at/around Step 16, before `steps-sort`, mirroring
menu-mode Re-Run Remediation Pass step (e). **Acceptance:** immediately after a fresh wizard, every
`plan.phase-6-finalize.steps` entry carries an explicit `lane`; verified on a fresh-project fixture.

**Interaction note to document (do NOT drop):** `sync-defaults` also deep-merges every `default_on`
finalize step back into `steps` with `lane: off` (the "infra steps must be opt-in" behavior —
[[feedback_infra_steps_must_be_opt_in]]), so a narrower preset ends up with all default steps present
but non-preset ones `off`. Add a one-line note in the wizard docs so the post-materialize step count
isn't surprising. This preserves the effective running set (it does not turn steps on).

## Expected Surface

- `manage-config/scripts/_cmd_system_plan.py` (D1 — `cmd_project` set branch)
- `manage-config/scripts/_cmd_sync_defaults.py` (D2 — invocation path; likely no logic change to the pass itself)
- `marshall-steward/references/wizard-flow.md` (D2 — Step 16 wiring) + steward SKILL.md + docs one-liner
- tests: manage-config unit (D1 regression) + wizard/sync-defaults fixture (D2)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: in-flight PLAN-06 (ci-pr-safe-merge) shares the manage-config/steward config surface
  but different files — mostly disjoint; rebase only if both touch `configuration.adoc` / config-defaults
  docs. Fully disjoint from PLAN-05 (terminal-title) and PLAN-04 (docs-contract).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-07-steward-wizard-config-integrity.md"
```

## Status Trail

- plan_marshall_plan_id: steward-wizard-config-integrity
- pr: #932 (MERGED 2026-07-18, squash via merge-queue)
- landing: SHIPPED — D1 (project set unknown_field rejection) + D2 (first-run wizard sync-defaults lane materialization) both landed. Self-review caught + fixed an undocumented-error-contract gap in-run (manage-config SKILL.md + api-reference.md now document unknown_field).
