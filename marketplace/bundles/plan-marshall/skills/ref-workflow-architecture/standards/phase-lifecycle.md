# Phase Lifecycle Patterns

Shared patterns that apply to all 6 phases. Individual phase SKILL.md files reference this document for boilerplate behavior and override only where phase-specific logic differs.

See [phases.md](phases.md) for the phase flow model and transition rules.

---

## Phase Enforcement Template

All phase skills enforce these rules. Phase-specific enforcement blocks may add additional constraints.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip phase transitions — use `manage-status transition`, never set status directly
- Never improvise script subcommands — use only those documented in the skill's workflow steps
- Never use Edit/Write tools on `.plan/` files (triggers permission prompts)

**Constraints:**
- Scripts are invoked only through `python3 .plan/execute-script.py` with 3-part notation
- Phase transitions are sequential: 1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-finalize
- All script output uses TOON format — parse `status` field to determine success/error
- User review gates (config flags: `plan_without_asking`, `execute_without_asking`, `finalize_without_asking`) must be respected

---

## Phase Entry Protocol

### Q-Gate Check (phases 2-6)

Before starting phase work, check for unresolved Q-Gate findings from the previous phase. Phase 1-init skips this (no previous phase).

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase {current_phase} --resolution pending
```

**If pending findings exist:**

For each finding, resolve it based on the action taken:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} --phase {current_phase} \
  --detail "{what was done to address this finding}"

python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:{phase_skill}:qgate) Finding {hash_id} [{source}]: {resolution} — {detail}"
```

Resolution values: `taken_into_account`, `fixed`, `deduplicated`, `reopened`.

**If no pending findings:** Continue to the next step.

### Phase Handshake Verify (phases 2-6)

After the Q-Gate check, verify the handshake captured by the previous phase:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase {previous_phase_key} --strict
```

**On `status: ok`**: Continue to the next step.

**On `status: drift`**: Stop the phase immediately. Surface the `diffs[]` table to the user verbatim. **Do NOT rationalize the differences. Do NOT auto-continue.** The only valid responses are:
- **Authorized override**: user confirms the drift is legitimate, then run `phase_handshake capture --override --reason "{user rationale}"` on the previous phase and re-enter the current phase.
- **Manual investigation**: user investigates the root cause and corrects the drift before re-entry.

Drift is a *signal*, not a *nuisance*. `--strict` makes the script exit non-zero so tooling that swallows TOON still sees the failure.

**On `status: skipped`**: Log a warning to work.log and continue. Skipped means "first-time rollout, manual transition, or post-clear capture" — not an error, but worth surfacing so the audit trail is honest.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[HANDSHAKE] (plan-marshall:{phase_skill}) Verify skipped — no capture for {previous_phase_key}"
```

### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:{phase_skill}) Starting {phase_name} phase"
```

---

## Phase Completion Protocol

After all phase-specific steps are done, execute this 4-step completion sequence:

### Step 1: Transition Phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed {phase_key}
```

Where `{phase_key}` is: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, or `6-finalize`.

### Step 2: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:{phase_skill}) {phase_name} phase complete — {summary}"
```

The `{summary}` should include phase-specific metrics (e.g., "plan created with {domain} domain", "{N} deliverables, Q-Gate: pass", "{M} tasks created").

### Step 3: Log Separator

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

### Step 4: Phase Handshake Capture

Capture invariants so the next phase's entry protocol can verify them:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase {phase_key}
```

Returns `status: success` with the captured invariants. Re-running a phase replaces the previous row. See [`../../plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md) for the full contract, storage format, and invariant registry.

---

## Error Handling Convention

All phase skills use a `| Scenario | Action |` table for error documentation:

| Pattern | Standard Action |
|---------|----------------|
| Script returns `status: error` | Report error to caller with details. Do not proceed. |
| Q-Gate findings pending | List findings, resolve or ask user. Do not skip. |
| Build verification failure | Report failing tests/compilation. Do not commit broken state. |
| Max iterations reached | Return with current state. Do not loop further. |
| Push failure | Report error. Never force-push as fallback. |
| Missing prerequisites | Return error with details on what is needed. |

Phase-specific error scenarios should be added to each phase's own error table, following this format.
