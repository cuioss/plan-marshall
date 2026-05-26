---
name: default:lessons-capture
description: Record lessons learned
order: 60
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Lessons Capture

Pure executor for the `lessons-capture` finalize step. Records lessons learned from the implementation. Advisory only — does not block.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — the failure mode documented in lesson `2026-04-29-23-002` (silent swallowing of `wrong_parameters` rejections). "Log and continue" is the prohibited anti-pattern.

See also `standards/lessons-integration.md` for conceptual guidance on when and what to capture.

This document carries body-level skip-conditional branching: when no lesson-bearing signals are present, the Signal Gate below short-circuits with `outcome=skipped` before any LLM dispatch. Dispatcher-level activation is controlled by `phase-6-finalize/SKILL.md` Step 3 and is driven by presence of `lessons-capture` in `manifest.phase_6.steps`; reaching this body is necessary but no longer sufficient to trigger the `post-run-review` LLM.

**Conditional dispatch based on signal presence**: Whenever this step appears in the manifest, the dispatcher runs the body on every Phase 6 entry, but the body itself decides whether the LLM dispatch fires. The decision reads three signal sources: (1) pending Q-Gate findings via `manage-findings qgate list --resolution pending` (`total_count`), (2) the `automated-review` step's outcome via `manage-status read` (treating outcomes other than `done` and non-zero promoted-comment counts as signals), and (3) script-failure clusters in the work log via `manage-logging read --type work` (counting distinct failing script notations in `[FAILED]` markers). When all three counts are zero, the Signal Gate emits `mark-step-done --outcome skipped --display-detail "no lesson-bearing signals"` and returns early; otherwise the body proceeds into the three-step path-allocate flow. The composer in `manage-execution-manifest:compose` includes `lessons-capture` for every change-type that produces non-trivial work (the rule-1 early-terminate analysis path is the only documented exclusion).

This step runs as a Task dispatch under the `post-run-review` sub-key (resolved via `manage-config effort resolve-target --phase phase-6-finalize --role post-run-review`) with a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. The dispatcher emits the standardized `[DISPATCH]` work-log line at the call site — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) for the canonical emission contract. The `post-run-review` sub-key bundles lessons-capture with retrospective — both workflows look back at the full plan history and ride the same level. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — lessons capture is advisory and never blocks the rest of the pipeline.

### `[DISPATCH]` log line (emitted by the dispatcher)

The phase-6-finalize SKILL.md dispatcher emits the line below immediately before invoking this workflow:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=post-run-review workflow=plan-marshall:phase-6-finalize/workflow/lessons-capture.md plan_id={plan_id}"
```

## Execution

### Signal Gate (early-return guard)

Before loading `manage-lessons` and BEFORE any `Task:` dispatch, evaluate three signal sources. When ALL THREE counts are zero, short-circuit with `outcome=skipped` and return `status: success, lessons_recorded: 0` — do NOT enter the three-step add flow below.

**Signal 1 — pending Q-Gate findings**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --resolution pending
```

Parse `total_count` from the TOON output. Non-zero ⇒ continue past the gate.

**Signal 2 — `automated-review` step outcome**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  read --plan-id {plan_id}
```

Locate the `automated-review` step under `metadata.phase_steps["6-finalize"]`. Treat any of the following as a non-zero signal ⇒ continue: (a) `outcome` is anything other than `done`, (b) `display_detail` reports a non-zero promoted-comment count (e.g. `"3 comments promoted"`). Outcome `done` with zero promoted comments ⇒ signal count zero.

**Signal 3 — script-failure clusters**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type work
```

Scan the returned log lines for `[FAILED]` markers and bucket them by distinct failing script notation (the `bundle:skill:script` token in the `[FAILED]` line). The cluster count is the number of distinct notations. Non-zero ⇒ continue.

**Skip branch — all three counts zero**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome skipped \
  --display-detail "no lesson-bearing signals"
```

Return immediately with:

```toon
status: success
display_detail: "no lesson-bearing signals"
lessons_recorded: 0
```

Do NOT load `manage-lessons`, do NOT enter the three-step add flow, and do NOT dispatch the `post-run-review` Task.

**Continue branch — at least one signal non-zero**: proceed to the `Skill: plan-marshall:manage-lessons` load below and run the standard three-step add flow.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-lessons"
```

```
Skill: plan-marshall:manage-lessons
```

Lessons are added in **three steps** via the path-allocate flow. This is the single canonical sequence — there is no inline `--detail` form and no alternative API variant. The body is staged to a plan-scoped file with the Write tool, then applied to the lesson via `set-body`, so arbitrary markdown (sections with `##` headings, fenced code blocks, multi-paragraph prose) never passes through a shell argument.

### Step 1 — Allocate the lesson file

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{bundle}:{skill}" \
  --category {bug|improvement|anti-pattern} \
  --title "{concise summary}"
```

Required flags: `--component`, `--category`, `--title`. The call creates a file with the metadata header and the `# {title}` heading already in place (body is empty) and returns both the lesson `id` and absolute `path` in the TOON output.

### Step 2 — Stage the body via the Write tool

Parse `id` from Step 1's TOON output. Use the Write tool to write the lesson body markdown to a plan-scoped staging file:

```
Write {plan_dir}/work/lesson-body-{id}.md
```

Where `{plan_dir}` is the absolute path to the active plan directory and `{id}` is the lesson identifier from Step 1 (e.g., `lesson-body-2026-04-27-10-005.md`). The body may contain arbitrary markdown — `##` section headings, fenced code blocks, lists, multiple paragraphs — because the Write tool delivers the content directly without shell quoting.

### Step 3 — Apply the staged body via `set-body`

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id {id} \
  --file {plan_dir}/work/lesson-body-{id}.md
```

The script reads the staged file from disk and replaces the body section of the lesson, preserving the metadata header and `# {title}` heading written in Step 1. On success the call returns the lesson `path` and `body_bytes_written`.

### Anti-patterns — prohibited shortcuts

Do **not** attempt to compress the three steps into a single shell-mediated write. The following shortcuts are explicitly prohibited because they either trip the host platform's path-validation heuristic on `#`-bearing markdown, mangle whitespace and code fences, or otherwise corrupt the lesson body:

- `python -c "open(...).write(...)"` — inline Python that smuggles body content through the shell argument vector. Forbidden.
- `$(printf ...)` — command substitution to assemble multi-line markdown. Forbidden.
- Heredocs containing lines that begin with `#` — markdown headings inside `<<EOF` blocks trip the bare-comment heuristic and trigger security prompts. Forbidden.

Use the three-step path-allocate flow above (Step 1 `add` → Step 2 Write tool → Step 3 `set-body --file`) for every lesson body. There is no `--detail`, no `--detail-file`, no inline-body variant on `add` — the path-allocate flow is the single supported API for non-trivial bodies.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the capture outcome. The payload differs by branch:

**Branch A — one or more lessons recorded**: `{N}` is the count of `manage-lessons add` calls made in this step. `{lesson_ids}` is the comma-joined list of lesson identifiers returned by those calls (e.g. `lesson-2026-04-17-005,lesson-2026-04-17-006`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "{N} lesson(s) recorded ({lesson_ids})"
```

**Branch B — no lessons recorded** (advisory step; nothing lesson-worthy emerged from this plan):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "no lessons recorded"
```

**Branch C — no lesson-bearing signals (skip)**: emitted by the Signal Gate above when all three signal counts are zero. Recorded with `--outcome skipped` rather than `--outcome done` to distinguish the structural short-circuit from a normal advisory pass-through:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome skipped \
  --display-detail "no lesson-bearing signals"
```

## Output

```toon
status: success | error
display_detail: "<{N} lessons recorded or `no lessons recorded` or `no lesson-bearing signals`>"
lessons_recorded: {N}
```

The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above.
