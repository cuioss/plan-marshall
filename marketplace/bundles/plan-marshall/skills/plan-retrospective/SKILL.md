---
name: plan-retrospective
description: Opt-in plan quality audit — analyzes artifacts, logs, metrics, chat, and invariants; compiles report and seeds lessons
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
order: 995
---

# Plan Retrospective Skill

**Role**: Opt-in plan quality audit. Analyzes a plan's artifacts, logs, metrics, chat history, and invariant outcomes; compiles a `quality-verification-report.md` (or `quality-verification-report-audit-{timestamp}.md` in archived mode) and proposes lessons-learned drafts.

**Design intent**: Python scripts produce deterministic TOON fragments (facts). The orchestrator loads aspect reference docs on-demand so the LLM can synthesize judgement from those facts. Scripts never judge; references never run code.

## Enforcement

**Execution mode**: Select a mode (finalize-step live, user-invocable live, archived) from the Input Contract, dispatch the 11 aspect references in the documented order, compile the report, propose lessons, then emit the mode-appropriate termination (mark-step-done tail for finalize-step mode only).

**Prohibited actions**:
- Never re-run invariant capture. Read `status.metadata.phase_handshake` or `status.metadata.invariants` directly — invariants are already captured by phase transitions.
- Never write to archived plan directories. Archived mode writes the report next to the archived plan, but the plan state itself is read-only.
- Never call `mark-step-done` in archived mode or user-invocable live mode — only the finalize-step mode emits the handshake tail.
- Never silently skip aspect dispatch. If a script fails, record the failure in the report under "Script failure analysis" and continue.
- Do not modify any .plan/ files directly — all plan state access goes through `manage-*` scripts and the scripts in this skill.

**Constraints**:
- Strictly comply with all rules from `plan-marshall:dev-general-practices`.
- Report filename is `quality-verification-report.md` in live modes (overwrite on repeat invocation) and `quality-verification-report-audit-{YYYYMMDDTHHMMSSZ}.md` in archived mode.

## Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--plan-id` | string | Conditional | Live plan identifier. Required for finalize-step mode and user-invocable live mode. |
| `--archived-plan-path` | string | Conditional | Absolute path to an archived plan directory (`.plan/archived-plans/{date}-{plan_id}/`). Required for archived mode. Mutually exclusive with `--plan-id`. |
| `--session-id` | string | No | Optional session identifier. When present, the chat-history aspect is dispatched; otherwise it is skipped. |
| `--iteration` | integer | No | Finalize-step iteration counter. Forwarded by `phase-6-finalize`; ignored by user-invocable and archived modes. |

**Mode resolution**:
- `--plan-id` provided, invoked by `phase-6-finalize` → **finalize-step mode** (emit `mark-step-done` tail).
- `--plan-id` provided, invoked by user or command → **user-invocable live mode** (no `mark-step-done` tail).
- `--archived-plan-path` provided → **archived mode** (no `mark-step-done` tail, timestamped filename).

Mode detection heuristic: when `--iteration` is present alongside `--plan-id`, treat as finalize-step mode; otherwise user-invocable live mode.

## Workflow

### Step 1: Validate Inputs and Resolve Plan Paths

Validate mutual exclusion of `--plan-id` and `--archived-plan-path`. Resolve:
- Live modes: `plan_dir = .plan/local/plans/{plan-id}/`
- Archived mode: `plan_dir = --archived-plan-path` (verify directory exists).

Log start:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:plan-retrospective) Starting retrospective — mode={mode}"
```

(Skip logging in archived mode — the archived plan's log files are write-frozen.)

### Step 2: Collect Plan Artifacts

Script: `plan-marshall:plan-retrospective:collect-plan-artifacts`. Produces a manifest TOON of all files present in the plan directory, classified by kind (status, references, tasks, logs, metrics, reports). Both live and archived modes are supported via the `--mode` flag.

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-plan-artifacts \
  run --plan-id {plan_id} --mode live
```

or for archived mode:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-plan-artifacts \
  run --archived-plan-path {path} --mode archived
```

Capture the manifest TOON for later aspects.

### Step 3: Dispatch Aspects (in order)

Before dispatching aspects, initialize the fragment bundle. `collect-fragments init` creates an empty TOON bundle file at the mode-appropriate path: live mode writes to `{plan_dir}/work/retro-fragments.toon`; archived mode writes to an OS tmp directory so the archived plan stays read-only. Capture the returned `bundle_path` for use in Step 4.

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  init --plan-id {plan_id} --mode {live|archived} [--archived-plan-path {path}]
```

Parse `bundle_path` from the TOON output.

For each aspect below, produce a TOON fragment on disk at `work/fragment-{aspect}.toon` (live mode) or the tmp equivalent (archived mode), then register it via `collect-fragments add`. Fragments are persisted to disk so that `compile-report` in Step 4 can consume them from a single bundle file assembled by `collect-fragments`.

| Order | Aspect | Script(s) | Reference |
|-------|--------|-----------|-----------|
| 1 | Artifact consistency | `check-artifact-consistency` | `references/artifact-consistency.md` |
| 2 | Log analysis | `analyze-logs` | `references/log-analysis.md` |
| 3 | Invariant outcomes | `summarize-invariants` | `references/invariant-check-summary.md` |
| 4 | Plan efficiency | (LLM on metrics.md + logs) | `references/plan-efficiency.md` |
| 5 | Request-result alignment | (LLM on request.md + solution_outline.md + logs) | `references/request-result-alignment.md` |
| 6 | LLM-to-script opportunities | (LLM on logs + scripts) | `references/llm-to-script-opportunities.md` |
| 7 | Logging gap analysis | (LLM on references + logs) | `references/logging-gap-analysis.md` |
| 8 | Script failure analysis | (LLM on work/script logs) | `references/script-failure-analysis.md` |
| 9 | Permission prompt analysis | (LLM on description or session) | `references/permission-prompt-analysis.md` |
| 10 | Chat history (conditional) | (LLM on session transcript) | `references/chat-history-analysis.md` |
| 11 | Lessons proposal | (LLM on compiled fragments) | `references/lessons-proposal.md` |

**Aspect 10** is skipped when `--session-id` is absent.

**Per-aspect capture pattern**:

**Deterministic aspects (1-3, script-backed)** — pipe the script's stdout to the fragment file, then register it:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:{script} \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-{aspect}.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

**LLM aspects (4-9 and 11)** — load the aspect reference via `Read`, produce the TOON fragment body per the reference's schema, emit it with the `Write` tool to `work/fragment-{aspect}.toon`, then register:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

**Aspect 10 (chat-history, conditional)** — when `--session-id` is present, follow the LLM pattern above (Write fragment file, then `collect-fragments add`).

### Step 4: Compile Report

Finalize the fragment bundle and pass it to `compile-report run`. `collect-fragments finalize` prints the `bundle_path` and the list of registered aspects in its TOON output; use that path as the `--fragments-file` input to `compile-report`.

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  finalize --plan-id {plan_id}
```

Parse `bundle_path` from the TOON output, then:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:compile-report \
  run --plan-id {plan_id} --mode {live|archived} --fragments-file {bundle_path}
```

The script returns the report's absolute path and the list of sections written. Section order follows `references/report-structure.md`.

**Cleanup**: `compile-report run` auto-deletes the fragment bundle after a successful report write. On failure paths (before the report is flushed to disk), the bundle is retained so the aspect fragments remain available for debugging.

### Step 5: Propose Lessons (optional, interactive)

Load `references/lessons-proposal.md`. For each proposed lesson, allocate a lesson file via the two-step path-allocate flow and write the body directly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:plan-retrospective" --category improvement \
  --title "{lesson title}"
```

Parse `path` from the output and `Write` the body. The `references/lessons-proposal.md` document defines the prompting rules and category choices.

In non-interactive finalize-step mode, emit lessons automatically only when confidence is high (documented in the reference). User-invocable mode uses `AskUserQuestion` for each draft.

### Step 6: Mode-Specific Termination

**Finalize-step mode**: emit the `mark-step-done` handshake so the `phase_steps_complete` invariant is satisfied:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step plan-retrospective --outcome done \
  --display-detail "{N} findings across {M} aspects"
```

**User-invocable live mode** and **archived mode**: skip the handshake. Emit only the final TOON contract below.

### Step 7: Return Results

```toon
status: success
plan_id: {plan_id or basename of archived_plan_path}
mode: {finalize-step|user-invocable|archived}
report_path: {absolute path to report}
aspects_dispatched: N
lessons_proposed: M
lessons_recorded: K
```

On error:

```toon
status: error
plan_id: {id}
mode: {mode}
error: {code}
message: {human-readable}
```

## Related

- `plan-marshall:phase-6-finalize` — optional orchestrator that dispatches this skill when the bundle-opt-in finalize step is enabled.
- `plan-marshall:manage-status` — source of `status.metadata` for invariant summary.
- `plan-marshall:manage-logging` — canonical log reader.
- `plan-marshall:manage-lessons` — lessons draft/seed API.
- `plan-marshall:manage-metrics` — metrics.md is an input to the plan-efficiency aspect.
