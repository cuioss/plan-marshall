---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflow — Action: lessons-aggregate

Workflow for the `lessons-aggregate` action (aggressive cross-lesson aggregation + superseded-stub prune in a single command).

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts resolve `.plan/` via the uniform cwd walk-up (ADR-002) — the nearest ancestor of cwd containing `.plan/local`. The orchestrator runs on the main checkout in phases 1-4 (resolving main's `.plan/`) and pins cwd to the worktree in phase-5+ (resolving the moved-in worktree copy); do **NOT** pass routing flags to `manage-*`, and never use `env -C`. Build / CI / Sonar scripts accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Action: lessons-aggregate

Aggressive cross-lesson aggregation in a single command: classify the active lessons corpus, ask the user once for confirmation, then for each multi-lesson group rewrite the primary lesson's body and title, supersede the absorbed lessons, and optionally prune the resulting `.md` stubs. Tombstones at `.tombstones/{id}.json` are NEVER touched — they remain as the audit trail for every supersede event.

This action is the orchestrator counterpart to the read-only `manage-lessons aggregate` verb (see [`plan-marshall:manage-lessons:references/aggregate-analysis.md`](../../manage-lessons/references/aggregate-analysis.md) for the classifier rules, signal-priority order, primary-pick tie-breakers, and merged-body-preview template).

**Step 1**: Run the read-only classifier and capture the TOON output:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons aggregate \
  --top-n 5
```

Parse `groups[]` (full list, regardless of `top-n`) and `top_n_commands[]` (priority-ordered headline commands surfaced at Step 5). Each group carries `primary_id`, `primary_title`, `absorb_count`, `tier`, `enacted`, `absorbed[]{lesson_id, title, reason}`, and `merged_body_preview`. `tier` is the group's strongest grouping signal (`cross-ref` | `shared-component` | `shared-standards-dir` | `shared-workflow-boundary`); `enacted` is `true` only for the `cross-ref` tier — weaker-tier groups are co-location suggestions, not auto-applied merges.

If `groups[]` is empty, log the no-op decision and return immediately:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) No multi-lesson groups detected — nothing to aggregate"
```

**Step 2**: Present per-group confirmation via `AskUserQuestion`. Each group is an independently selectable option, so the user enacts only the groups they trust rather than accepting or rejecting the whole batch. Build two questions.

The first question is a `multiSelect: true` group picker with one option per group. The option label is the group's `primary_id`; the description carries `absorb_count`, an absorbed-id summary truncated to 8 with `... and N more`, and a trust marker derived from `enacted`:

- `enacted: true` (cross-ref tier) → marker `recommended — direct cross-reference`
- `enacted: false` (weaker tier) → marker `suggestion — {tier} co-location only, not auto-applied`

The second question is a single-select prune control.

```text
AskUserQuestion:
  questions:
    - question: |
        ## Aggressive Lesson Aggregation

        The classifier found {len(groups)} multi-lesson group(s). Select the groups to enact — each selected group's primary lesson is rewritten to absorb the others, and the absorbed lessons are superseded. Weaker-tier groups (co-location only) are NOT pre-selected; opt in deliberately. Selecting nothing cancels.
      options:
        {for each group in groups:}
        - label: "{primary_id}"
          description: |
            absorb {absorb_count} lesson(s) — {trust_marker}
            {for each absorbed in group.absorbed[:8]:}
            {absorbed.lesson_id}: {absorbed.title} ({absorbed.reason})
            {if len(group.absorbed) > 8:}
            ... and {len(group.absorbed) - 8} more
      multiSelect: true
    - question: |
        ## Prune superseded stubs?

        After enacting the selected groups, remove the superseded `.md` stubs? Tombstones at `.tombstones/{id}.json` are preserved either way.
      options:
        - label: "Prune"
          description: "Run cleanup-superseded with --retention-days 0 after enacting the selected groups"
        - label: "Keep stubs"
          description: "Leave the superseded .md stubs in place"
      multiSelect: false
```

The trust marker primes the user against the over-aggressive default: only `cross-ref` groups are marked `recommended`; every weaker-tier group is a `suggestion` that defaults to opt-in (not pre-selected). The absorbed-id list is truncated to 8 items per group with a `... and N more` suffix, keeping large-group prompts readable while preserving enough context to decide.

An empty multi-select (no groups chosen) is treated as Cancel. Log and return:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) User selected no groups — no changes applied"
```

**Step 3**: For each group the user selected in the first question (the selected subset of `groups[]`):

1. Compose the new aggregated title from the primary's existing title plus the absorbed sub-task list. The composer joins the primary title with a parenthesised summary of the absorbed lessons (e.g., `"{primary_title} (aggregated with {N} related lessons)"` for large groups, or `"{primary_title} (with: {absorbed_id_1}, {absorbed_id_2})"` for small groups). Compose deterministically — repeated runs over the same group produce identical titles.

2. Stage the merged body to a plan-temp file (avoids shell-quoting concerns for arbitrary markdown):

   ```text
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

**Step 4**: Drive the prune from the second question's answer. If the user selected "Prune", run the cleanup with a zero-day retention to immediately remove the superseded `.md` stubs (tombstones at `.tombstones/{id}.json` are preserved by the script):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  --retention-days 0
```

Log the prune decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Prune complete — removed superseded .md stubs (tombstones preserved)"
```

If the user selected "Keep stubs", log the deferred decision instead:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Prune skipped — superseded .md stubs left in place by user request"
```

**Step 5**: Display the priority-ordered top-N command list captured from Step 1's `top_n_commands[]`. Surface it as a numbered list so the user can pick the next plan to work on:

```text
Next-up plans (priority-ordered):

1. /plan-marshall:plan-marshall lesson={primary_id_1}
2. /plan-marshall:plan-marshall lesson={primary_id_2}
...

Note: tombstones at `.tombstones/{id}.json` are preserved for every superseded lesson — historical references resolve by id even after the redirect stub is gone.
```

Log the final outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-aggregate) Aggregation complete — {selected_count} group(s) enacted, {len(top_n_commands)} headline command(s) surfaced"
```

Where `{selected_count}` is the number of groups the user selected in Step 2's first question.

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<aggregated {N} lessons, pruned {M} stubs>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch.
