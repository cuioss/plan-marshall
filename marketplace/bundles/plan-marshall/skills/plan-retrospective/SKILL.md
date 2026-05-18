---
name: plan-retrospective
description: Opt-in plan quality audit — analyzes artifacts, logs, metrics, chat, and invariants; compiles report and seeds lessons
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
order: 995
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Plan Retrospective Skill

**Role**: Opt-in plan quality audit. Analyzes a plan's artifacts, logs, metrics, chat history, and invariant outcomes; compiles a `quality-verification-report.md` (or `quality-verification-report-audit-{timestamp}.md` in archived mode) and proposes lessons-learned drafts.

**Design intent**: Python scripts produce deterministic TOON fragments (facts). The orchestrator loads aspect reference docs on-demand so the LLM can synthesize judgement from those facts. Scripts never judge; references never run code.

## Enforcement

**Execution mode**: Select a mode (finalize-step live, user-invocable live, archived) from the Input Contract, dispatch the 12 aspect references in the documented order, compile the report, propose lessons, then emit the mode-appropriate termination (mark-step-done tail for finalize-step mode only).

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

## Dispatch shape: 9 aspects iterate inside one envelope

This workflow dispatches under `--phase phase-6-finalize --role post-run-review` as **one** `execution-context-{level}` envelope. The `post-run-review` sub-key bundles retrospective with lessons-capture — both workflows look back at the full plan history and ride the same level. The 9 LLM analytical aspects (metrics, decision/work logs, references vs deliverables, deliverable vs lesson alignment, scope-deviation footprint, behavioural observations, execution-context dispatch audit, chat-history aspect when `--session-id` is present, lesson-quality audit) iterate **in-context inside that single envelope** — the orchestrator never spawns N × envelope per aspect. Bundling matches granularity Heuristic 2 (steps share context): every aspect reads the same plan artefacts, runs the same skill loads, and contributes to the same final retrospective document. Per-aspect dispatch would pay 9× envelope cost with no parallelism payoff. See [`../extension-api/standards/dispatch-granularity.md`](../extension-api/standards/dispatch-granularity.md) § 3.

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

**Canonical plan-status read** — when this workflow needs to read plan status (current phase, metadata, worktree binding) it MUST use the `manage-status` script's `read` subcommand. The supported invocation is:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Do not extrapolate `status get`, `manage_status get`, or `manage-status:status` — none of those exist. The canonical script notation is the 3-part form `plan-marshall:manage-status:manage_status` (the third segment matches the on-disk script filename `manage_status.py`), and the only read verb is `read`. The full canonical-forms entry for `manage-status` (covering `read`, `metadata --get --field`, `transition`, `get-worktree-path`, `change-type-heuristic`, and friends) lives in [`dev-general-practices/standards/argument-naming.md`](../dev-general-practices/standards/argument-naming.md#manage--scripts) — that table is the regression guard against the invented-verb drift that motivated this entry (see lesson `2026-05-14-00-001`). Future maintainers editing this workflow MUST cross-check any new `manage-status` call against that table before committing.

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

Before dispatching aspects, initialize the fragment bundle. `collect-fragments init` creates an empty TOON bundle file at the mode-appropriate path: live mode writes to `{plan_dir}/work/retro-fragments.toon`; archived mode writes to an OS tmp directory so the archived plan stays read-only. Capture the returned `bundle_path` for use in Step 4. The mode is persisted into the bundle by `init`, so subsequent register and finalize calls read it back automatically and accept only `--plan-id` and the fragment inputs.

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
| 10 | Direct gh/glab usage | `direct-gh-glab-usage` | `references/direct-gh-glab-usage.md` |
| 11 | Execution-context dispatch audit | (LLM on logs + dispatch decisions) | `standards/execution-context-dispatch-audit.md` |
| 12 | Manifest decisions (conditional) | `check-manifest-consistency` | `standards/manifest-crosscheck.md` |
| 13 | Chat history (conditional) | (LLM on session transcript) | `references/chat-history-analysis.md` |
| 14 | Lessons proposal | (LLM on compiled fragments) | `references/lessons-proposal.md` |

The Execution-context dispatch audit (aspect 11) consumes the `[DISPATCH]` work-log lines emitted by every dispatch site per [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) — that standard is the authoritative source for the line shape, and this aspect is its enforcement consumer. Report readers tracing an audit finding back to its evidence land in `dispatch-logging.md` § "Emission contract" for the canonical log-line format.

**Aspect 12 (manifest decisions)** is skipped when `execution.toon` is absent. When present, the aspect loads the manifest via `plan-marshall:manage-execution-manifest:manage-execution-manifest read --plan-id {plan-id}` and pairs it with matching `(plan-marshall:phase-4-plan:manifest)` decision-log entries — manifest = WHAT was decided, decision.log = WHY. The cross-check engine is `plan-marshall:plan-retrospective:check-manifest-consistency` which evaluates each manifest assumption against the actual end-of-execute diff and emits one finding per violation. See `standards/manifest-crosscheck.md` for the cross-check matrix.

**Aspect 13** is skipped when `--session-id` is absent.

**Per-aspect capture pattern**:

**Deterministic aspects (1-3 and 10, script-backed)** — pipe the script's stdout to the fragment file, then register it:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:{script} \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-{aspect}.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

**LLM aspects (4-9, 11, and 13)** — load the aspect reference via `Read`, produce the TOON fragment body per the reference's schema, emit it with the `Write` tool to `work/fragment-{aspect}.toon`, then register:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

**Aspect 12 (manifest-decisions, conditional)** — when `execution.toon` exists in the plan directory, run the deterministic script pattern with aspect name `manifest-decisions`:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:check-manifest-consistency \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-manifest-decisions.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect manifest-decisions --fragment-file work/fragment-manifest-decisions.toon
```

Skip the aspect entirely when the manifest file is absent.

**Aspect 13 (chat-history, conditional)** — when `--session-id` is present, first resolve the absolute transcript path via the canonical resolver, then follow the LLM pattern above (Write fragment file, then `collect-fragments add`).

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session \
  transcript-path --session-id {session_id}
```

Parse `transcript_path` from the TOON output and pass it to the LLM analysis prompt as a concrete absolute file path — the LLM `Read`s by absolute path with no discovery step. On `status: error\nerror: transcript_not_found`, degrade gracefully: emit a fragment with `status: skipped` and `reason: transcript_unavailable` per `references/chat-history-analysis.md`. Never substitute Bash file discovery (`ls`, `find`, Glob) for the resolver — the resolver is the only sanctioned lookup mechanism for the session JSONL.

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

Load `references/lessons-proposal.md`. Recording proceeds in two sub-steps: **5a** classifies each proposal against the existing corpus, and **5b** records only what the classification admits.

#### Step 5a: Classify (required before any recording)

Load `plan-marshall:manage-lessons:references/dedup-analysis.md` and classify every proposal into exactly one of three statuses:

| Status | Meaning | Caller action |
|--------|---------|---------------|
| `new` | No existing lesson covers this component + root cause | Proceed to 5b `manage-lessons add` |
| `merge_into` | An existing lesson shares component + root cause (`target_id` recorded) | Skip add; `Edit` target lesson file to append `## Recurrence — YYYY-MM-DD ({plan_id})` section |
| `already_closed` | Existing lesson filed AND code fix has since landed (`target_id` recorded) | Skip add; record target_id in report; delete stale lesson file (requires user confirmation in finalize-step mode) |

Dedup-gate enforcement is documented in `references/lessons-proposal.md` ("Dedup gate (required before recording)" section) and authoritatively specified in `dedup-analysis.md`. Recording without classification is prohibited.

#### Step 5b: Record (gated by 5a)

Only `status: new` proposals reach `manage-lessons add`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:plan-retrospective" --category improvement \
  --title "{lesson title}"
```

Parse `path` from the output and `Write` the body. `references/lessons-proposal.md` defines the prompting rules and category choices. `merge_into` proposals are applied via `Edit` on the target file; `already_closed` proposals are surfaced in the report and the stale lesson file at `.plan/local/lessons-learned/{target_id}.md` is deleted (requires user confirmation in finalize-step mode because deletion is destructive).

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
display_detail: "<{aspects} aspects, {lessons_recorded} lessons recorded>"
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
display_detail: "<retrospective error: {code}>"
plan_id: {id}
mode: {mode}
error: {code}
message: {human-readable}
```

## Output

Step 7 (above) is the single source of truth for the return TOON. The minimum contract every workflow doc that implements `ext-point-execution-context-workflow` MUST return is:

```toon
status: success | error
display_detail: "<{aspects_dispatched} aspects, {lessons_recorded} lessons recorded>"
```

`display_detail` shape on success: `"{aspects_dispatched} aspects, {lessons_recorded} lessons recorded"` (e.g. `"8 aspects, 3 lessons recorded"`); ≤80 chars, ASCII, no trailing period.

## Related

- `plan-marshall:phase-6-finalize` — optional orchestrator that dispatches this skill when the bundle-opt-in finalize step is enabled.
- `plan-marshall:manage-status` — source of `status.metadata` for invariant summary.
- `plan-marshall:manage-logging` — canonical log reader.
- `plan-marshall:manage-lessons` — lessons draft/seed API.
- `plan-marshall:manage-metrics` — metrics.md is an input to the plan-efficiency aspect.
