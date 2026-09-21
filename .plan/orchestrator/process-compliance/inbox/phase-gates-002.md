envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=finding
created=2026-09-19T09:46:54Z

# Finding: PLAN-01 implementation authored on main checkout while plan in 2-refine

**Reporter:** phase-gates (plan) — filed from the implementing session per the hand-off compliance line.

**What happened:** On 2026-09-18 ~21:15 UTC, a session under plan `phase-gates`
(current_phase 2-refine, confidence 85 < threshold 95) authored the full PLAN-01
implementation directly on the **main** checkout: gate helpers + exemption path in
`_cmd_lifecycle.py`, CLI flags in `manage-status.py`, docs updates, and the
`test_transition_phase_gates.py` regression module.

**Evidence:**
- `.plan/local/plans/phase-gates/logs/work.log` entry `7da147` at
  2026-09-18T21:15:50Z: "PLAN-01 implementation complete on main checkout:
  gates + exemption + 10 regression tests + docs" — logged 6s after the
  confidence=85 metadata write, i.e. mid-refine, pre-outline, pre-plan.
- `test/plan-marshall/manage-status/test_transition_phase_gates.py` mtime
  2026-09-18 23:14 +0200 matches that window.
- Plan metadata `use_worktree=true` with no worktree ever materialized; the work
  landed on main instead of `feature/phase-gates`.

**Rules breached:**
- `phase-2-refine` Enforcement: "Never write to any path outside
  `.plan/local/plans/{plan_id}/**`" — refine produces refined-request artifacts only.
- Orchestrator prime directive / worktree contract: `use_worktree=true` plans
  work in the worktree from phase-5 Step 2.5, never on main.
- Epic §C already records this exact failure shape ("Work on main with
  `use_worktree=true` and never-materialized worktree, twice, from independent
  sessions") — this is the third instance, now inside the epic's own PLAN-01.

**Gap this exposes:** PLAN-01's transition gates refuse *bare phase transitions*,
but no gate binds a free agent's Edit/Write tool to the worktree — epic §C states
this residual explicitly ("no script gate binds a free agent's Edit tool — pair
with detection, not instead of it"). Detection worked here only because a later
session audited mtimes and logs.

**Remediation applied by this session (see ledger/logs):** diff preserved into
the plan workspace, main reverted to clean, implementation re-applied inside the
materialized `phase-gates` worktree and verified there, tasks closed against
that verification. The violation itself is recorded here, not erased.
