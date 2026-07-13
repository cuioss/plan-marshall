# Upgrade Flow

The `upgrade` verb runs the full post-change reconciliation in ONE flow after a
marketplace change: regenerate `target/claude` + the executor, reconcile
`marshal.json`, verify (executor preflight + content-drift report), then run the
existing landing cycle. The verb is pure orchestration glue over already-shipped
machinery — it FIRST calls the deterministic planner `upgrade.py plan` to obtain
the fixed four-stage plan with per-stage gate dispositions, then drives each
stage's existing machinery honoring those dispositions.

This reference is loaded from two entry points (see [`../SKILL.md`](../SKILL.md)):
Main Menu option 5 ("Upgrade"), and the `upgrade` early verb check (which passes
the `integrate` value from `/marshall-steward upgrade [integrate=true]`).

`{repo_root}` below is the main-checkout repository root the steward is running
against. All git invocations use the explicit `git -C {repo_root} …` form (never
`cd {repo_root} && git …`), all mutations go through scripts (never hand-edits),
and all CI/PR operations go through the `tools-integration-ci:ci` abstraction
(never `gh`/`glab` directly).

## The four stages

```text
  Stage 1  regenerate-targets   generate.py --target claude + generate_executor generate   [mutating]
  Stage 2  reconcile-config     manage-config sync-defaults + steps-sort                    [mutating]
                                └─ nested gate: build-map re-seed (still prompts)
  Stage 3  verify               generate_executor preflight + content_drift_cli report      [read-only]
  Stage 4  land                 Read references/landing-cycle.md and execute AS-IS          [mutating]
                                └─ nested gates: land/leave + branch-reuse (still prompt)
```

## Step 0: Obtain the stage plan

Call the deterministic planner FIRST, passing the resolved `integrate` value
(`true` when the invocation carried `integrate=true`, otherwise `false`):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:upgrade plan --integrate {integrate}
```

See the [`../SKILL.md`](../SKILL.md) Canonical invocations (`upgrade — plan`) for
the verb shape. Parse the returned `stages[4]{order,key,name,mutating,top_level_gate,nested_gates}`
list. Each stage's `top_level_gate` is the disposition this flow honors below:
`prompt` (ask before running the stage) or `suppressed` (run without the
top-level prompt).

## Gate contract

- **Plain mode** (`/marshall-steward upgrade`) — every stage's `top_level_gate`
  is `prompt`. Before running each of the four stages, present a top-level gate
  `AskUserQuestion` (Proceed / Skip this stage / Abort the upgrade).
- **`integrate=true`** (`/marshall-steward upgrade integrate=true`) — every
  stage's `top_level_gate` is `suppressed`. Run all four stages end-to-end
  WITHOUT the top-level prompts.
- **`integrate=true` suppresses ONLY the four top-level stage gates.** The
  **nested** gates are `integrate`-invariant and STILL prompt under
  `integrate=true`: the Stage 2 `build-map` re-seed gate and the Stage 4 landing
  land/leave + branch-reuse gates. `integrate=true` is therefore **not** a
  globally-unattended mode — it collapses the four stage-boundary prompts, not
  the safety gates that guard destructive or hand-editable state.
- **Do NOT modify the reused sub-flows to add suppression.** The reused
  machinery (the `build-map` drift gate, `landing-cycle.md`) keeps its own
  prompts exactly as-is; this flow never edits those sub-flows to honor
  `integrate`.

### Per-stage top-level gate

For each stage, before running its machinery:

- **`top_level_gate: prompt`** — present:

  ```text
  AskUserQuestion:
    question: "Run upgrade Stage {order} — {name}?"
    header: "Upgrade — Stage {order}"
    options:
      - label: "Proceed"
        description: "Run this stage's machinery"
      - label: "Skip this stage"
        description: "Move to the next stage without running this one"
      - label: "Abort"
        description: "Stop the upgrade; report the partial state"
    multiSelect: false
  ```

  - **Proceed** → run the stage.
  - **Skip this stage** → move to the next stage.
  - **Abort** → follow "Partial-failure and abort handling" below.

- **`top_level_gate: suppressed`** → run the stage without prompting.

## Stage 1: regenerate-targets (mutating)

Honor the Stage 1 top-level gate, then regenerate the Claude target tree and the
executor:

```bash
python3 marketplace/targets/generate.py --target claude --output target/claude
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
```

See the `tools-script-executor` Canonical invocations (`generate_executor` →
`generate`) for the verb shape.

> **Session restart after executor regeneration.** Regenerating the executor may
> change the emitted agent set. The registry is session-pinned at session start,
> so surface the session-restart guardrail — see [`../SKILL.md`](../SKILL.md) §
> "Session Restart Required After Executor / Agent Changes" — after this stage
> when the executor was regenerated.

## Stage 2: reconcile-config (mutating)

Honor the Stage 2 top-level gate, then reconcile `marshal.json`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config sync-defaults
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config steps-sort
```

See the `manage-config` Canonical invocations (`sync-defaults`, `steps-sort`) for
the verb shapes. Both are idempotent and byte-stable on an already-current config.

**Nested gate — `build-map` re-seed (STILL prompts under `integrate=true`).**
Compute the drift between the persisted `build.map` and the live-tree derivation,
then gate any re-seed behind an `AskUserQuestion` so deliberate hand-edits are
never clobbered — the same read-only drift gate the Re-Run Remediation Pass step
(c) uses (see [`../SKILL.md`](../SKILL.md)):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

- **`in_sync: true`** → no drift; continue silently.
- **`in_sync: false`** → show the added/removed-glob diff, then prompt:

  ```text
  AskUserQuestion:
    question: "The persisted build.map differs from the live-tree derivation. Re-seed it?"
    header: "build.map drift"
    options:
      - label: "Yes, re-seed"
        description: "Overwrite build.map with the live derivation"
      - label: "No, leave as-is"
        description: "Keep the persisted build.map (preserves deliberate hand-edits)"
    multiSelect: false
  ```

  - **Yes** → re-seed via the force path:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed --force
    ```

  - **No** → leave the persisted `build.map` untouched.

This nested gate prompts even when `integrate=true` suppressed the Stage 2
top-level gate.

## Stage 3: verify (read-only)

Honor the Stage 3 top-level gate, then run the two read-only verification checks.
Neither mutates the working tree.

**(a) Executor / config staleness preflight:**

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor preflight
```

See the `tools-script-executor` Canonical invocations (`generate_executor` →
`preflight`) for the verb shape.

**(b) Content-drift report** — the thin CLI over the content-drift engine.
Exit `0` means the emitted `target/claude/` markdown matches a fresh emit; exit
`1` means drift was detected (or `target/claude` is not generated), with the
drifted/missing/orphan paths named in the TOON report:

```bash
python3 marketplace/targets/claude/content_drift_cli.py
```

If drift is reported, the fix is to re-run Stage 1's `generate.py` emit — the
source `.md` files under `marketplace/bundles/` are canonical and MUST NOT be
edited to satisfy the gate.

## Stage 4: land (mutating)

Honor the Stage 4 top-level gate, then run the existing landing cycle AS-IS:

```text
Read references/landing-cycle.md
```

Execute that reference's procedure unchanged. Its nested gates — the land/leave
`AskUserQuestion` and the non-base branch-reuse confirmation — STILL prompt even
when `integrate=true` suppressed the Stage 4 top-level gate. Do NOT modify
`landing-cycle.md` to honor `integrate`.

## Partial-failure and abort handling

The upgrade flow performs **no rollback**. On a stage failure (a stage's
machinery exits non-zero or reports an error) OR an operator **Abort**:

1. **STOP at the failed / aborted stage.** Do NOT run any later stage.
2. **Report the partial state** — which stages completed, which stage stopped
   the flow, and the specific failure (e.g. the failing command and its error).
3. **Report the manual resume path** — any already-completed stages' mutations
   remain on disk (regenerated target/executor, reconciled config); the operator
   can re-run `/marshall-steward upgrade` after resolving the failure to continue
   from a clean state, or run the remaining stages' machinery by hand.

No stage is un-done. The reconciliation is forward-only.

## End-of-flow behavior

When all four stages complete (or the flow stops per the partial-failure
contract), return control to the steward's end-of-flow behavior:

- Invoked from **Main Menu option 5** → return to Main Menu Page 1.
- Invoked from the **`upgrade` early verb check** → the run ends (the verb
  bypassed the menu).
