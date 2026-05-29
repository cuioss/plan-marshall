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
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

See also `standards/lessons-integration.md` for conceptual guidance on when and what to capture.

**Dispatcher-level Signal Gate precondition (B4)**: This body NO LONGER carries the three-signal Signal Gate. The deterministic three-signal precondition (pending Q-Gate findings, automated-review outcome, script-failure clusters) has been relocated to `phase-6-finalize/SKILL.md` Step 3 § "Lessons-capture Signal Gate" (item 4b in the dispatch loop) so the envelope spawn cost is avoided when all three signals are zero. The semantics are preserved bit-for-bit: when the dispatcher observes all three counts zero, it records `mark-step-done --outcome skipped --display-detail "no lesson-bearing signals"` directly and this workflow body is NOT dispatched. Reaching this body therefore PROVES at least one signal was non-zero — the body proceeds straight into the three-step path-allocate flow below without re-evaluating any signals.

**Gate counts as runtime inputs**: The dispatcher forwards the three observed counts on the prompt body so the body never re-issues the signal queries. The available runtime inputs are:

- `signal_qgate_pending_count` — integer; sum across `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`.
- `signal_automated_review_count` — integer (0 or 1); 1 when the `automated-review` step had an outstanding/non-done state (outcome anything other than `done`, or its `display_detail` reports a non-zero promoted-comment count) OR when the run remediated one or more actionable review-bot findings (`manage-findings list --type pr-comment --resolution fixed` returned `filtered_count >= 1`). The remediated-in-run trigger fires the signal even when the step `outcome=done` and zero comments are outstanding at gate-evaluation time — a review-bot finding caught-and-fixed in-run is exactly the slipped-then-caught defect class lessons-capture exists to record.
- `signal_script_failure_clusters_count` — integer; number of distinct failing script notations across three marker classes: `[FAILED]` work-log lines, `[ERROR] ... script_failure` lines (the per-call non-zero-exit marker emitted by phase error handling), and `voluntary_checkpoint → error` reclassifications (dispatch-boundary no-progress reclassifications). A notation that fails under more than one marker class counts once (union dedup by distinct notation).

These counts MAY be consulted as context when authoring the lesson bodies (e.g., to focus recording on whichever signal source dominated), but the body MUST NOT re-issue `manage-findings qgate list`, `manage-status read`, or `manage-logging read --type work` to recompute them — the dispatcher already paid that cost.

This step runs as a Task dispatch under the `post-run-review` sub-key (resolved via `manage-config effort resolve-target --phase phase-6-finalize --role post-run-review`) with a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. The dispatcher emits the standardized `[DISPATCH]` work-log line at the call site — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) for the canonical emission contract. The `post-run-review` sub-key bundles lessons-capture with retrospective — both workflows look back at the full plan history and ride the same level. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — lessons capture is advisory and never blocks the rest of the pipeline.

### `[DISPATCH]` log line (emitted by the dispatcher)

The phase-6-finalize SKILL.md dispatcher emits the line below immediately before invoking this workflow:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=post-run-review workflow=plan-marshall:phase-6-finalize/workflow/lessons-capture.md plan_id={plan_id}"
```

## Execution

The dispatcher-level Signal Gate (see header above, and `phase-6-finalize/SKILL.md` Step 3 item 4b) has already certified that at least one of the three signal sources is non-zero before this body runs. Proceed to the `Skill: plan-marshall:manage-lessons` load below, then run the three-gate lesson-creation policy before allocating any new lesson.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-lessons"
```

```
Skill: plan-marshall:manage-lessons
```

### Run the lesson-creation policy gates first

Before allocating a new lesson, run the canonical three-gate sequence defined in [`../../manage-lessons/standards/lesson-creation-policy.md`](../../manage-lessons/standards/lesson-creation-policy.md): Gate 1 (dedup against the existing corpus), Gate 2 (active-plan check), then Gate 3 (create). Do not restate the gate mechanics here — follow the standard.

- **Gate 1 → `merge_into`**: extend the existing lesson (append a `## Recurrence` section / broaden scope) instead of adding a new one. Record nothing new; this is a Branch B2 outcome below.
- **Gate 1 → `already_closed`**: follow the standard's closed-lesson contract (deletion requires user confirmation). Branch B2 outcome.
- **Gate 2 → covering active plan**: fold the observation into that plan; do not file a standalone lesson. Branch B2 outcome.
- **Gates 1 and 2 both clear**: proceed to the three-step path-allocate add flow below — this IS Gate 3.

### Gate 3 — Create: the three-step path-allocate add flow

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

**Branch B2 — folded into an existing lesson or active plan, no new lesson recorded**: the gate sequence resolved the observation at Gate 1 (`merge_into` / `already_closed`) or Gate 2 (covering active plan), so no new lesson was allocated:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "folded into existing lesson/plan, no new lesson"
```

**Branch C — no lesson-bearing signals (skip)**: NOT emitted by this body. The `outcome=skipped` recording is now the dispatcher's responsibility (see `phase-6-finalize/SKILL.md` Step 3 item 4b) and fires before this workflow is dispatched. This body only runs when at least one signal was non-zero, so its `mark-step-done` calls are exclusively Branches A or B above.

## Output

```toon
status: success | error
display_detail: "<{N} lessons recorded or `no lessons recorded`>"
lessons_recorded: {N}
```

The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above.
