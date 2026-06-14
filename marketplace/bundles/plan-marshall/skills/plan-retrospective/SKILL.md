---
name: plan-retrospective
description: Opt-in plan quality audit — analyzes artifacts, logs, metrics, chat, and invariants; compiles report and seeds lessons
user-invocable: true
mode: workflow
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
- Strictly comply with all rules from `plan-marshall:dev-agent-behavior-rules`.
- Report filename is `quality-verification-report.md` in live modes (overwrite on repeat invocation) and `quality-verification-report-audit-{YYYYMMDDTHHMMSSZ}.md` in archived mode.

## Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Dispatch shape: 9 aspects iterate inside one envelope

This workflow dispatches under `--phase phase-6-finalize --role post-run-review` as **one** `execution-context-{level}` envelope. The `post-run-review` sub-key bundles retrospective with lessons-capture — both workflows look back at the full plan history and ride the same level. The 8 LLM analytical aspects (metrics, decision/work logs, references vs deliverables, deliverable vs lesson alignment, scope-deviation footprint, behavioural observations, execution-context dispatch audit, chat-history aspect when `--session-id` is present, lesson-quality audit) iterate **in-context inside that single envelope** — the orchestrator never spawns N × envelope per aspect. Bundling matches granularity Heuristic 2 (steps share context): every aspect reads the same plan artefacts, runs the same skill loads, and contributes to the same final retrospective document. Per-aspect dispatch would pay 8× envelope cost with no parallelism payoff. See [`../extension-api/standards/dispatch-granularity.md`](../extension-api/standards/dispatch-granularity.md) § 3.

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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Do not extrapolate `status get`, `manage_status get`, or `manage-status:status` — none of those exist. The canonical script notation is the 3-part form `plan-marshall:manage-status:manage-status` (the third segment matches the on-disk script filename `manage-status.py`), and the only read verb is `read`. The full canonical-forms entry for `manage-status` (covering `read`, `metadata --get --field`, `transition`, `get-worktree-path`, `change-type-heuristic`, and friends) lives in [`dev-agent-behavior-rules/standards/argument-naming.md`](../dev-agent-behavior-rules/standards/argument-naming.md#manage--scripts) — that table is the regression guard against the invented-verb drift that motivated this entry (see lesson `2026-05-14-00-001`). Future maintainers editing this workflow MUST cross-check any new `manage-status` call against that table before committing.

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
| 8 | Script failure analysis | `script-failure-analysis` | `references/script-failure-analysis.md` |
| 9 | Permission prompt analysis | (LLM on description or session) | `references/permission-prompt-analysis.md` |
| 10 | Direct gh/glab usage (Surfaces A+B: plan logs + plan diff) | `direct-gh-glab-usage` | `references/direct-gh-glab-usage.md` |
| 11 | Execution-context dispatch audit (both directions: spawns rode the envelope AND DISPATCHED steps were dispatched) | (LLM on logs + dispatch decisions + phase_steps) | `standards/execution-context-dispatch-audit.md` |
| 12 | Manifest decisions (conditional) | `check-manifest-consistency` | `standards/manifest-crosscheck.md` |
| 13 | Chat history (conditional) | (LLM on session transcript) | `references/chat-history-analysis.md` |
| 14 | Lessons proposal | (LLM on compiled fragments) | `references/lessons-proposal.md` |

The Execution-context dispatch audit (aspect 11) consumes the `[DISPATCH]` work-log lines emitted by every dispatch site per [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) — that standard is the authoritative source for the line shape, and this aspect is its enforcement consumer. The aspect asserts dispatch discipline in **both directions**: that every spawn that DID happen rode the canonical `execution-context-{level}` envelope, AND that every finalize/execute step classified DISPATCHED actually WAS dispatched. The inverse-coverage half (`dispatch_coverage_violation` category) cross-references the SKILL's own dispatched/inline classification against the `status.metadata.phase_steps["6-finalize"]` outcome records — a step marked done with zero matching `[DISPATCH]` evidence is flagged as inline-where-dispatch-was-required. Report readers tracing an audit finding back to its evidence land in `dispatch-logging.md` § "Emission contract" for the canonical log-line format.

> **Coverage contract**: the Artifact-consistency aspect (aspect 1) is the *declared-vs-achieved coverage* comparison — declared in-scope files (`Affected files:`) vs the plan's actual footprint — which is the deterministic item-coverage half of the *thoroughness* dial, graded to the FLOOR. The footprint is derived live from the plan's worktree (`{base}...HEAD` ∪ porcelain) when one is on disk, falling back to the legacy `references.modified_files` key only for archived plans created before the ledger was removed. See the two-dial scope × thoroughness contract (ladders, grade-to-the-floor rule, coupling constraint) in [`../dev-agent-behavior-rules/standards/thoroughness.md`](../dev-agent-behavior-rules/standards/thoroughness.md).

**Aspect 12 (manifest decisions)** is skipped when `execution.toon` is absent. When present, the aspect loads the manifest via `plan-marshall:manage-execution-manifest:manage-execution-manifest read --plan-id {plan-id}` and pairs it with matching `(plan-marshall:phase-4-plan:manifest)` decision-log entries — manifest = WHAT was decided, decision.log = WHY. The cross-check engine is `plan-marshall:plan-retrospective:check-manifest-consistency` which evaluates each manifest assumption against the actual end-of-execute diff and emits one finding per violation. See `standards/manifest-crosscheck.md` for the cross-check matrix.

**Aspect 13** is skipped when `--session-id` is absent.

> **Achieved thoroughness**: there is no mechanical achieved-thoroughness measurement. The *achieved* side of coverage is the floor-graded self-report defined in [`../dev-agent-behavior-rules/standards/thoroughness.md`](../dev-agent-behavior-rules/standards/thoroughness.md) § Floor-Graded Self-Report; the Artifact-consistency aspect (aspect 1, above) supplies the deterministic declared-vs-actual footprint (derived live from the worktree, or the legacy `references.modified_files` key for older archived plans) that the self-report grades against.

**Domain-contributed aspects (merged after the fixed table, gated by plan domain)**:

The fixed aspect table above is domain-invariant — it runs for every plan. Domain bundles may contribute ADDITIONAL deterministic, script-backed aspects via the `provides_retrospective_aspects()` extension point (see [`../extension-api/standards/ext-point-retrospective.md`](../extension-api/standards/ext-point-retrospective.md)). Merge them after the fixed table and before compiling the report:

1. **Resolve the audited plan's domain.** Read the plan's domain from its task metadata — the `domain` field on the plan's tasks (e.g., `plan-marshall-plugin-dev`). In live mode, read a representative task via `manage-tasks`; in archived mode, read the domain from the archived `status.metadata` / task files. When the plan has no resolvable domain, skip the merge entirely (no domain aspects apply).

2. **List domain-contributed aspects** across all extensions:

   ```bash
   python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
     list-retrospective-aspects
   ```

   Parse the `aspects[]` rows from the TOON output. Each row carries `aspect`, `domain`, `script`, `reference`, `description`, and `order`.

3. **Filter by the audited plan's domain.** Keep only rows whose `domain` matches the plan's domain. Skip every aspect from a non-matching domain. The remaining aspects are deterministic script-backed fragments — run each exactly like the built-in script-backed aspects (1-3, 8, 10): invoke its `script` notation with `run --mode {live|archived}` plus the resolution flags, pipe stdout to `work/fragment-{aspect}.toon`, then register it via `collect-fragments add --aspect {aspect}`.

   ```bash
   python3 .plan/execute-script.py {script} \
     run --plan-id {plan_id} --mode {live|archived} > work/fragment-{aspect}.toon
   python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
     add --plan-id {plan_id} --aspect {aspect} --fragment-file work/fragment-{aspect}.toon
   ```

   For example, a `plan-marshall-plugin-dev` plan picks up the `wrapper-tangle` aspect (`pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan`) — the former Surface C of the generic `direct-gh-glab-usage` aspect, now homed in pm-plugin-development. Plans of other domains skip it.

**Per-aspect capture pattern**:

**Deterministic aspects (1-3, 8, and 10, script-backed)** — pipe the script's stdout to the fragment file, then register it:

The `script-failure-analysis` script (aspect 8) consumes the plan's `script-execution.log` directly and classifies non-zero-exit calls by stderr signature (`invalid choice:` → `invented_subcommand`; `the following arguments are required:` → `missing_required_flag`; `unrecognized arguments:` → `invented_flag`; non-argparse exit-1 → `script_internal_error`). The TOON fragment carries deduped `findings[]` and seed `lessons[]` for downstream classification; the orchestrator does NOT inject LLM judgement at this point. See `references/script-failure-analysis.md` for the finding shape; the LLM aspects that follow may augment the script-emitted findings with source-component tracing.

The `analyze-logs` script (aspect 2) additionally parses the plan's **folded-in global logs** (the `{prefix}-YYYY-MM-DD.log` files folded into `<plan_dir>/logs/` at integrate-into-main) and surfaces per-plan operational signals under `global_log_signals` (error/non-INFO lines, slow calls, fixture leaks). This per-plan view **complements** the cross-plan `global-log-analysis` audit check in `audit-archived-plan-retrospectives` — the two are non-overlapping facets: this aspect surfaces each plan's own phases 5-6 signals from its folded-in copies, while the audit check parses the live `.plan/local/logs/` corpus with cross-plan execution-window attribution covering phases 1-4. See `references/log-analysis.md` § "Folded-in global logs".

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:{script} \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-{aspect}.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

**LLM aspects (4-7, 9, 11, and 13)** — load the aspect reference via `Read`, produce the TOON fragment body per the reference's schema, emit it with the `Write` tool to `work/fragment-{aspect}.toon`, then register:

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

**Aspect 13 (chat-history, conditional)** — when `--session-id` is present, resolve the absolute transcript path by constructing the canonical Claude Code path pattern `~/.claude/projects/{cwd-slug}/{session_id}.jsonl` (where `{cwd-slug}` is the absolute project cwd with each `/` replaced by `-`). Attempt to read the file directly; if absent, try a parent-directory glob under `~/.claude/projects/` for cross-cwd recovery. Never substitute Bash file discovery (`ls`, `find`, Glob) for this resolution — the canonical path derivation is the only sanctioned lookup mechanism for the session JSONL.

Run the `extract-chat-signal.py` signal-extraction pre-pass against the resolved `transcript_path` to obtain the tier decision and the reduced transcript:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:extract-chat-signal run \
  --transcript-path {abs_transcript_path}
```

The pre-pass output drives the two-tier degradation path: when `no_signal == false` AND `over_budget == false` (Tier 1), feed `reduced_transcript` to the LLM analysis prompt and synthesize the `status: success` fragment; otherwise (Tier 2 — transcript absent, no signal, or still over the 2 MiB read budget), emit a `status: skipped` fragment carrying the canonical skip-reason token. The two-tier path and the normative skip-reason token contract (`transcript_too_large` for a size-driven skip vs `transcript_unavailable` for a genuine data absence, and how downstream aggregation MUST distinguish them) are specified in `references/chat-history-analysis.md` — see [`references/chat-history-analysis.md`](references/chat-history-analysis.md) §§ "Two-Tier Degradation Path" and "Skip-Reason Token Contract". Do not restate the token semantics here.

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

### Step 5.5: Stalled-lesson-sourced-plan detection (detection-and-prompt)

When the audited plan is itself a **stalled lesson-sourced plan**, its relocated lesson is trapped inside the plan directory and out of the active corpus. The signal is self-evident from the plan's own `status.json` — no new script-backed aspect is needed. Detect it from the status already read in Step 1:

- `status.metadata.plan_source` matches the lesson-id pattern `YYYY-MM-DD-HH-NNN` (the plan is lesson-sourced), AND
- `status.current_phase` is one of `5-execute` / `6-finalize` with that phase's row `status != done` (the plan is stalled in a non-terminal state).

When BOTH conditions hold, surface the stranded-lesson signal in the report and prompt the user (live modes only — skip the prompt in archived mode, which is read-only):

```
AskUserQuestion:
  question: "This plan is a stalled lesson-sourced plan ({plan_id}) — its lesson(s) are trapped out of the active corpus. Resume the plan or restore the lesson(s)?"
  header: "Stalled lesson"
  options:
    - label: "Resume plan"
      description: "Continue the plan from its current phase ({current_phase}) to a terminal state"
    - label: "Restore lesson(s)"
      description: "Run restore-from-plan to return the lesson(s) to .plan/local/lessons-learned/"
  multiSelect: false
```

On **"Restore lesson(s)"**, invoke the inverse of `convert-to-plan`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan \
  --plan-id {plan_id}
```

This detection note is the per-plan counterpart of the corpus-wide tooling: `manage-lessons list-stalled` (see [`../manage-lessons/SKILL.md`](../manage-lessons/SKILL.md) § `list-stalled`) scans every plan for the same signal, and the `Action: cleanup` stalled-lesson restore pass (see [`../plan-marshall/workflow/planning.md`](../plan-marshall/workflow/planning.md) § "Action: cleanup" → "Stalled-lesson-sourced-plan restore") restores them in bulk. Keep this addition thin — it is a detection-and-prompt note, not a new script-backed aspect in the Step 3 table.

### Step 6: Mode-Specific Termination

**Finalize-step mode**: emit the `mark-step-done` handshake so the `phase_steps_complete` invariant is satisfied:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step plan-marshall:plan-retrospective --outcome done \
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

## Canonical invocations

The canonical argparse surface for the ten entry-point scripts this skill registers (twelve invocation forms — `collect-fragments` carries three sub-verbs). The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation". The single-aspect scripts share the same `run` flag surface; `collect-fragments` carries the `init` / `add` / `finalize` sub-verbs.

### extract-chat-signal — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:extract-chat-signal run \
  --transcript-path TRANSCRIPT_PATH [--read-budget-bytes READ_BUDGET_BYTES]
```

### check-manifest-consistency — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:check-manifest-consistency run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH] \
  [--diff-file DIFF_FILE] [--base-ref BASE_REF]
```

`--base-ref` is required when `--diff-file` is absent.

### script-failure-analysis — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:script-failure-analysis run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### check-artifact-consistency — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:check-artifact-consistency run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### analyze-logs — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:analyze-logs run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### summarize-invariants — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:summarize-invariants run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### collect-plan-artifacts — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-plan-artifacts run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### compile-report — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:compile-report run \
  --mode {live,archived} --fragments-file FRAGMENTS_FILE \
  [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH] [--session-id SESSION_ID]
```

### direct-gh-glab-usage — run

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:direct-gh-glab-usage run \
  --mode {live,archived} [--plan-id PLAN_ID] [--archived-plan-path ARCHIVED_PLAN_PATH] \
  [--base BASE] [--project-root PROJECT_ROOT] [--audit-plan-id AUDIT_PLAN_ID]
```

### collect-fragments — init

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments init \
  --plan-id PLAN_ID --mode {live,archived} [--archived-plan-path ARCHIVED_PLAN_PATH]
```

### collect-fragments — add

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id PLAN_ID --aspect ASPECT --fragment-file FRAGMENT_FILE \
  [--archived-plan-path ARCHIVED_PLAN_PATH] [--overwrite]
```

### collect-fragments — finalize

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments finalize \
  --plan-id PLAN_ID [--archived-plan-path ARCHIVED_PLAN_PATH]
```

## Related

- `plan-marshall:phase-6-finalize` — optional orchestrator that dispatches this skill when the bundle-opt-in finalize step is enabled.
- `plan-marshall:manage-status` — source of `status.metadata` for invariant summary.
- `plan-marshall:manage-logging` — canonical log reader.
- `plan-marshall:manage-lessons` — lessons draft/seed API.
- `plan-marshall:manage-metrics` — metrics.md is an input to the plan-efficiency aspect.
