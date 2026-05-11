---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflow — Action: lessons-aggregate

Workflow for the `lessons-aggregate` action (aggressive cross-lesson aggregation + superseded-stub prune in a single command). Extracted from `workflow/planning.md` to keep that file under the bloat threshold.

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Action: lessons-aggregate

Aggressive cross-lesson aggregation in a single command: classify the active lessons corpus, ask the user once for confirmation, then for each multi-lesson group rewrite the primary lesson's body and title, supersede the absorbed lessons, and optionally prune the resulting `.md` stubs. Tombstones at `.tombstones/{id}.json` are NEVER touched — they remain as the audit trail for every supersede event.

This action is the orchestrator counterpart to the read-only `manage-lessons aggregate` verb (see [`plan-marshall:manage-lessons:references/aggregate-analysis.md`](../../manage-lessons/references/aggregate-analysis.md) for the classifier rules, signal-priority order, primary-pick tie-breakers, and merged-body-preview template).

**Step 1**: Run the read-only classifier and capture the TOON output:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons aggregate \
  --top-n 5
```

Parse `groups[]` (full list, regardless of `top-n`) and `top_n_commands[]` (priority-ordered headline commands surfaced at Step 5). Each group carries `primary_id`, `primary_title`, `absorb_count`, `absorbed[]{lesson_id, title, reason}`, and `merged_body_preview`.

If `groups[]` is empty, log the no-op decision and return immediately:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) No multi-lesson groups detected — nothing to aggregate"
```

**Step 2**: Present a single batch confirmation via `AskUserQuestion`. Build the question body from the parsed `groups[]`:

```
AskUserQuestion:
  questions:
    - question: |
        ## Aggressive Lesson Aggregation

        The classifier found {len(groups)} multi-lesson group(s) whose work would land in a single plan. Proceeding will rewrite each primary lesson's body and title to absorb the others, then supersede the absorbed lessons.

        {for each group in groups:}
        ### {primary_id}: {primary_title}
        - Will absorb {absorb_count} lesson(s):
          {for each absorbed in group.absorbed[:8]:}
          - {absorbed.lesson_id}: {absorbed.title} ({absorbed.reason})
          {if len(group.absorbed) > 8:}
          - ... and {len(group.absorbed) - 8} more

        Planned prune count (when "Proceed and prune" is selected): {sum(absorb_count for group in groups)} superseded `.md` stub(s) — tombstones at `.tombstones/{id}.json` are preserved.

        How would you like to proceed?
      options:
        - label: "Proceed and prune"
          description: "Apply set-body + set-title + supersede for each group, then cleanup-superseded with --retention-days 0"
        - label: "Proceed but skip prune"
          description: "Apply set-body + set-title + supersede for each group; leave the superseded .md stubs in place"
        - label: "Cancel"
          description: "Make no changes"
      multiSelect: false
```

The absorbed-id list is truncated to 8 items per group with a `... and N more` suffix when the group has more than 8 absorbed lessons; this keeps the prompt readable for large groups while still giving the user enough context to decide.

If the user selects "Cancel", log and return:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) User cancelled — no changes applied"
```

**Step 3**: On "Proceed and prune" or "Proceed but skip prune", iterate over `groups[]`. For each group:

1. Compose the new aggregated title from the primary's existing title plus the absorbed sub-task list. The composer joins the primary title with a parenthesised summary of the absorbed lessons (e.g., `"{primary_title} (aggregated with {N} related lessons)"` for large groups, or `"{primary_title} (with: {absorbed_id_1}, {absorbed_id_2})"` for small groups). Compose deterministically — repeated runs over the same group produce identical titles.

2. Stage the merged body to a plan-temp file (avoids shell-quoting concerns for arbitrary markdown):

   ```
   Write(".plan/temp/aggregate-merged-bodies/{primary_id}.md", merged_body)
   ```

   Where `merged_body` is the full composed body (primary's body, followed by `## Sub-task: {absorbed_title} ({absorbed_id})` H2 sections for each absorbed lesson). The classifier already produces a 400-character preview for the AskUserQuestion; this step composes the full body the same way.

3. Apply the body rewrite:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
     --lesson-id {primary_id} \
     --file .plan/temp/aggregate-merged-bodies/{primary_id}.md
   ```

4. Apply the title rewrite:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-title \
     --lesson-id {primary_id} \
     --title "{aggregated_title}"
   ```

5. Supersede each absorbed lesson, citing the primary as the canonical replacement:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons supersede \
     --lesson-id {absorbed_id} \
     --by {primary_id} \
     --reason "Aggregated into {primary_title}"
   ```

   Run one `supersede` call per absorbed lesson in the group.

Log a decision line per group capturing the per-group outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Aggregated group {primary_id}: absorbed {absorb_count} lesson(s) — {absorbed_ids_joined}"
```

**Step 4**: If the user selected "Proceed and prune", run the cleanup with a zero-day retention to immediately remove the superseded `.md` stubs (tombstones at `.tombstones/{id}.json` are preserved by the script):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  --retention-days 0
```

Log the prune decision (or its absence):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Prune complete — removed superseded .md stubs (tombstones preserved)"
```

If the user selected "Proceed but skip prune", log the deferred decision instead:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Prune skipped — superseded .md stubs left in place by user request"
```

**Step 5**: Display the priority-ordered top-N command list captured from Step 1's `top_n_commands[]`. Surface it as a numbered list so the user can pick the next plan to work on:

```
Next-up plans (priority-ordered):

1. /plan-marshall:plan-marshall lesson={primary_id_1}
2. /plan-marshall:plan-marshall lesson={primary_id_2}
...

Note: tombstones at `.tombstones/{id}.json` are preserved for every superseded lesson — historical references resolve by id even after the redirect stub is gone.
```

Log the final outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Aggregation complete — {len(groups)} group(s) processed, {len(top_n_commands)} headline command(s) surfaced"
```

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<aggregated {N} lessons, pruned {M} stubs>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch.
