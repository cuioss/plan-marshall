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

Lessons are added in **two steps**. This is the single canonical flow — there is no inline `--detail` form and no alternative API variant.

### Step A — Allocate the lesson file

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{bundle}:{skill}" \
  --category {bug|improvement|anti-pattern} \
  --title "{concise summary}"
```

Required flags: `--component`, `--category`, `--title`. The call creates a file with the metadata header and the `# {title}` heading already in place (body is empty) and returns an absolute `path` in the TOON output.

### Step B — Write the body directly to the returned path

Parse `path` from the TOON output of Step A and use the Write tool to append the lesson body to that file. The body may contain arbitrary markdown: `##` section headings, fenced code blocks, lists, multiple paragraphs. Because the body is delivered through the Write tool rather than a shell argument, Claude Code's path-validation heuristic for `#`-lines inside quoted arguments is not triggered and rich markdown bodies pass through safely.

Do not attempt to smuggle the body into the Step A call (no `--detail`, no `--detail-file`, no second subcommand). Any such variant is intentionally absent — the single path-allocate + Write-tool flow is the supported API.

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
