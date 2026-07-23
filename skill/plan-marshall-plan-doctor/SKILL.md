---
name: plan-marshall-plan-doctor
description: Diagnose plan artifacts (TASK-*.json) for unresolved lesson-ID references and other plan-level data integrity defects
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Plan Doctor Skill

**Role**: Post-hoc diagnostic for plan artifacts. Walks `TASK-*.json` files for one or all plans, scans `title` and `description` for lesson-ID-shaped tokens, verifies each token against the live `manage-lessons` inventory, and emits structured findings for any tokens that resolve to non-existent lessons.

In addition to the TASK-level lesson-ID sweep, `scan --all` also runs three plan-directory-shape diagnostics:

- **`orphan-plan-directory`** — a subdirectory under `.plan/local/plans/` that lacks `status.json`, or has `status.json` but none of `request.md` / `references.json` / `solution_outline.md`.
- **`stuck-low-confidence-archive`** — a subdirectory under `.plan/local/archived-plans/` whose `status.json` has `metadata.confidence < 95` (or the project-configured threshold), every phase after `2-refine` is `pending`, and `metadata.archived_reason` is absent.
- **`dangling-worktree`** — a subdirectory under `.plan/local/worktrees/` whose corresponding `.plan/local/plans/{name}/` directory does not exist.

This skill complements the at-write-time validation in `manage-tasks` (which prevents new bad references) by sweeping plans that may already contain stale or phantom lesson-ID references introduced before the at-write check existed (or via direct file edits that bypassed `manage-tasks`).

## Enforcement

**Execution mode**: Select `scan` or `scan-task-file` based on inputs and execute immediately.

**Prohibited actions:**
- Do not re-implement lesson-ID detection — always import `scan_lesson_id_tokens` and `verify_lesson_ids_exist` from `tools-input-validation` (single source of truth — no duplication)
- Do not silently degrade to "no findings" when the live inventory is unavailable — propagate the typed `LessonInventoryUnavailable` / `LessonRegexAnchoringError` failures so live-anchor discipline is enforced
- Do not write findings outside the plan-scoped Q-Gate store — use `manage-findings qgate add` so they participate in the standard triage loop

**Constraints:**
- Strictly comply with `plan-marshall:persona-plan-marshall-agent` rules (one Bash command per call, no shell constructs, no improvisation)
- Findings are emitted to the Q-Gate store under phase `5-execute` so they surface in the Phase 5 triage path; the script also prints a TOON summary to stdout
- Exit non-zero (`1`) when `findings_count > 0` so CI / orchestrators can fail fast on regressions

## When to Use

- After a plan has been planned (Phase 4) but before execution (Phase 5), to catch stale lesson-ID references introduced by hand-edited TASK files
- During plan retrospectives to verify all referenced lessons still exist in the inventory
- Globally (across all plans) as a periodic data-integrity sweep

## Verbs

Script: `plan-marshall:plan-doctor:plan_doctor`

### scan

Scan TASK-*.json files for one plan or for every plan under `.plan/local/plans/`.

```bash
# Single plan
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan \
  --plan-id EXAMPLE-PLAN

# Every plan in the inventory
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan --all
```

**Parameters:**
- `--plan-id` (mutually exclusive with `--all`): Scan a single plan
- `--all` (mutually exclusive with `--plan-id`): Scan every plan under `.plan/local/plans/`
- `--no-emit` (optional): Skip emitting findings to the Q-Gate store; only print the TOON summary. Useful for read-only audits.

**Behavior:**
- For each TASK-*.json file, scans `title` + `description` for lesson-ID-shaped tokens via `scan_lesson_id_tokens`
- Verifies every token against the live `manage-lessons list` inventory via `verify_lesson_ids_exist`
- Tokens that resolve to non-existent lessons become findings (`rule: phantom_lesson_id`)
- When `--all` is passed, additionally sweeps the three plan-directory-shape rules described below (`orphan_plan_directory`, `stuck_low_confidence_archive`, `dangling_worktree`); these rules do NOT run on a single-plan `--plan-id` call
- Each finding is written to the Q-Gate store (`source: qgate`, `type: bug`, `severity: warning` for orphan/dangling/phantom; `severity: info` for stuck-low-confidence; `phase: 5-execute`) unless `--no-emit` is passed
- Findings whose `plan_id` does not have a live `.plan/local/plans/{plan_id}/` directory (dangling-worktree and stuck-low-confidence-archive cases) are emitted in the TOON payload but NOT written to a Q-Gate store — there is no destination plan-dir to receive them
- Exits `1` when any findings are produced; `0` otherwise

### Plan-directory-shape rules (`--all` only)

#### `orphan-plan-directory` (severity: warning)

Triggers when a subdirectory of `.plan/local/plans/` either:
- has no `status.json`, OR
- has `status.json` but none of `request.md`, `references.json`, `solution_outline.md` exist.

The finding carries a `remediation` field with one of three values:
- `rm_rf` — no `logs/` content; the partial init produced nothing worth keeping.
- `archive_with_reason` — `logs/` has content; archive with `manage-status archive --reason orphan-init-incomplete` (see [D2 — manage-status archive --reason](../manage-status/SKILL.md#archive)).
- `operator_review` — `status.json` claims `current_phase: 6-finalize` but artifacts are absent; needs operator decision (likely "stuck finalize on a shell" from a parallel session).

#### `stuck-low-confidence-archive` (severity: info)

Triggers when an archived plan (subdirectory of `.plan/local/archived-plans/`) meets ALL of:
- `status.json` has every phase after `2-refine` in `status: pending`.
- `status.metadata.confidence` is a number strictly less than `95` (the default threshold).
- `status.metadata.archived_reason` is missing or empty.

This is advisory only — the archive is a record of an operator decision. The finding carries `confidence` and `threshold` fields so the operator can decide whether to (a) restore + raise the threshold or (b) annotate the archive with `archived_reason`. **Do NOT auto-remediate.**

#### `dangling-worktree` (severity: warning)

Triggers when a subdirectory of `.plan/local/worktrees/` does not have a corresponding `.plan/local/plans/{name}/` directory. The likely cause is a cleanup race or a failed `git worktree remove` on a prior finalize. Operator should inspect the worktree for uncommitted work, then remove it.

### scan-task-file

Scan a single explicit TASK-*.json file. Useful for ad-hoc validation when a plan-id is not convenient (e.g., scratch files in `.plan/temp/`).

```bash
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan-task-file \
  --plan-id EXAMPLE-PLAN \
  --task-file /absolute/path/to/TASK-001.json
```

**Parameters:**
- `--plan-id` (required): Plan identifier the task file belongs to (used as the plan-id in findings; not used to resolve the path)
- `--task-file` (required): Absolute or repo-relative path to a single TASK-*.json file
- `--no-emit` (optional): Skip emitting findings; only print the TOON summary

**Behavior:**
- Identical scanning rules to `scan`, but operates on a single file
- Findings still go to the Q-Gate store under `--plan-id` so the standard triage loop can pick them up

## Output Contract (TOON)

Both verbs print:

```toon
status: success
checked_files: 12
findings_count: 4
findings[4]{plan_id,task_file,line,token,rule,reason,remediation,confidence,threshold}:
  EXAMPLE-PLAN,TASK-003.json,1,2099-01-01-00-001,phantom_lesson_id,phantom_lesson_id,,,
  EXAMPLE-PLAN,TASK-007.json,1,2099-12-31-23-999,phantom_lesson_id,phantom_lesson_id,,,
  doc-revamp,,,,orphan_plan_directory,orphan_plan_directory,operator_review,,
  2026-05-18-lesson,,,,stuck_low_confidence_archive,stuck_low_confidence_archive,,47.0,95.0
summary:
  plans_scanned: 1
  emit_to_qgate: true
```

The TOON table widens to the union of fields across all rule types — TASK-level rows leave the rule-specific cells empty, and rule-level rows leave the TASK-specific cells empty. The TOON parser surfaces each row as a dict keyed by the column names; missing cells parse as empty strings.

Errors (TOON, exit 1):

```toon
status: error
error: lesson_inventory_unavailable
message: "manage-lessons list exited 2: 'boom'"
```

| Field | Description |
|-------|-------------|
| `status` | `success` (always for non-fatal results) or `error` (fatal — see error table) |
| `checked_files` | Number of TASK-*.json files actually parsed |
| `findings_count` | Number of phantom lesson-ID references discovered |
| `findings[]{plan_id, task_file, line, token, rule, reason, remediation, confidence, threshold}` | Per-finding rows. `line` is `1` for phantom rows (the file is JSON; per-line attribution is best-effort). Rule-level rows leave TASK-specific cells empty. |
| `rule` | Identifies the diagnostic: `phantom_lesson_id`, `orphan_plan_directory`, `stuck_low_confidence_archive`, or `dangling_worktree`. Mirrors `reason` for backward compatibility. |
| `reason` | Same value as `rule` (retained for backward compatibility with the original single-rule contract). |
| `remediation` | Set only on `orphan_plan_directory` rows: `rm_rf`, `archive_with_reason`, or `operator_review`. |
| `confidence` / `threshold` | Set only on `stuck_low_confidence_archive` rows. |
| `summary.plans_scanned` | Distinct plans inspected |
| `summary.emit_to_qgate` | `true` when findings were emitted, `false` for `--no-emit` |

### Error codes

| Error | Meaning |
|-------|---------|
| `invalid_plan_id` | `--plan-id` failed canonical validation (kebab-case) |
| `plan_not_found` | The plan directory does not exist for `--plan-id` |
| `task_file_not_found` | `--task-file` does not exist on disk |
| `task_file_unreadable` | The file exists but failed to parse as JSON |
| `mutually_exclusive` | `--plan-id` and `--all` were both supplied |
| `lesson_inventory_unavailable` | The `manage-lessons list` subprocess failed — surfaces as a fatal error to enforce live-anchor discipline |
| `lesson_regex_anchored_to_drifted_inventory` | The canonical `LESSON_ID_RE` matches none of the live IDs — the regex shape has drifted from reality |

## Canonical invocations

The canonical argparse surface for `plan_doctor.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### scan

```bash
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan \
  [--plan-id PLAN_ID] [--all] [--no-emit]
```

### scan-task-file

```bash
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan-task-file \
  --plan-id PLAN_ID --task-file TASK_FILE [--no-emit]
```

## Cross-References

- **`plan-marshall:tools-input-validation`** — Owns `scan_lesson_id_tokens` and `verify_lesson_ids_exist` (the single source of truth for lesson-ID detection; this skill never re-implements either function)
- **`plan-marshall:manage-findings`** — Receives the Q-Gate findings (`qgate add`) so the standard Phase 5 triage loop can resolve them (FIX / SUPPRESS / ACCEPT)
- **`plan-marshall:manage-tasks`** — At-write-time validator (companion to this post-hoc sweep); together they cover both the prevention and detection paths for lesson-ID drift
- **Lessons** — The live-anchor discipline enforced here originates in lessons `2026-04-29-10-001` (regex/data drift surfacing as silent green) and `2026-05-03-21-002` (live-anchored test fixtures). See `standards/check-lesson-id-references.md` for the rationale and how to interpret/resolve findings.

## Standards (Load On-Demand)

```text
Read standards/check-lesson-id-references.md
```
