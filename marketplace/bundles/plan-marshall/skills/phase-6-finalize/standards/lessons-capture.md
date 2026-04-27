---
name: default:lessons-capture
description: Record lessons learned
order: 60
---

# Lessons Capture

Pure executor for the `lessons-capture` finalize step. Records lessons learned from the implementation. Advisory only — does not block.

See also `standards/lessons-integration.md` for conceptual guidance on when and what to capture.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `lessons-capture` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

**Unconditional dispatch when manifested**: Whenever this step appears in the manifest, the dispatcher runs it on every Phase 6 entry. It is NOT gated on PR state, CI status, Sonar gate result, or any earlier step's outcome — reaching Phase 6 is itself the trigger. The composer in `manage-execution-manifest:compose` includes `lessons-capture` for every change-type that produces non-trivial work (the rule-1 early-terminate analysis path is the only documented exclusion).

This step runs as a Task agent (`plan-marshall:lessons-capture-agent`) under a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — lessons capture is advisory and never blocks the rest of the pipeline.

## Execution

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

Do **not** attempt to compress the three steps into a single shell-mediated write. The following shortcuts are explicitly prohibited because they either trip Claude Code's path-validation heuristic on `#`-bearing markdown, mangle whitespace and code fences, or otherwise corrupt the lesson body:

- `python -c "open(...).write(...)"` — inline Python that smuggles body content through the shell argument vector. Forbidden.
- `$(printf ...)` — command substitution to assemble multi-line markdown. Forbidden.
- Heredocs containing lines that begin with `#` — markdown headings inside `<<EOF` blocks trip the bare-comment heuristic and trigger security prompts. Forbidden.

Use the three-step path-allocate flow above (Step 1 `add` → Step 2 Write tool → Step 3 `set-body --file`) for every lesson body. There is no `--detail`, no `--detail-file`, no inline-body variant on `add` — the path-allocate flow is the single supported API for non-trivial bodies.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the capture outcome. The payload differs by branch:

**Branch A — one or more lessons recorded**: `{N}` is the count of `manage-lessons add` calls made in this step. `{lesson_ids}` is the comma-joined list of lesson identifiers returned by those calls (e.g. `lesson-2026-04-17-005,lesson-2026-04-17-006`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "{N} lesson(s) recorded ({lesson_ids})"
```

**Branch B — no lessons recorded** (advisory step; nothing lesson-worthy emerged from this plan):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "no lessons recorded"
```
