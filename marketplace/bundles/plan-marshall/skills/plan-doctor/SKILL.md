---
name: plan-doctor
description: Diagnose plan artifacts (TASK-*.json) for unresolved lesson-ID references and other plan-level data integrity defects
user-invocable: true
---

# Plan Doctor Skill

**Role**: Post-hoc diagnostic for plan artifacts. Walks `TASK-*.json` files for one or all plans, scans `title` and `description` for lesson-ID-shaped tokens, verifies each token against the live `manage-lessons` inventory, and emits structured findings for any tokens that resolve to non-existent lessons.

This skill complements the at-write-time validation in `manage-tasks` (which prevents new bad references) by sweeping plans that may already contain stale or phantom lesson-ID references introduced before the at-write check existed (or via direct file edits that bypassed `manage-tasks`).

## Enforcement

**Execution mode**: Select `scan` or `scan-task-file` based on inputs and execute immediately.

**Prohibited actions:**
- Do not re-implement lesson-ID detection — always import `scan_lesson_id_tokens` and `verify_lesson_ids_exist` from `tools-input-validation` (single source of truth — no duplication)
- Do not silently degrade to "no findings" when the live inventory is unavailable — propagate the typed `LessonInventoryUnavailable` / `LessonRegexAnchoringError` failures so live-anchor discipline (lessons 2026-04-29-10-001 and 2026-05-03-21-002) is enforced
- Do not write findings outside the plan-scoped Q-Gate store — use `manage-findings qgate add` so they participate in the standard triage loop

**Constraints:**
- Strictly comply with `plan-marshall:dev-general-practices` rules (one Bash command per call, no shell constructs, no improvisation)
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
  --plan-id my-plan

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
- Tokens that resolve to non-existent lessons become findings
- Each finding is written to the Q-Gate store (`source: qgate`, `type: bug`, `severity: warning`, `phase: 5-execute`) unless `--no-emit` is passed
- Exits `1` when any findings are produced; `0` otherwise

### scan-task-file

Scan a single explicit TASK-*.json file. Useful for ad-hoc validation when a plan-id is not convenient (e.g., scratch files in `.plan/temp/`).

```bash
python3 .plan/execute-script.py plan-marshall:plan-doctor:plan_doctor scan-task-file \
  --plan-id my-plan \
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
findings_count: 2
findings[2]{plan_id,task_file,line,token,reason}:
  my-plan,TASK-003.json,1,2099-01-01-00-001,phantom_lesson_id
  my-plan,TASK-007.json,1,2099-12-31-23-999,phantom_lesson_id
summary:
  plans_scanned: 1
  emit_to_qgate: true
```

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
| `findings[]{plan_id, task_file, line, token, reason}` | Per-finding rows. `line` is `1` (the file is JSON; per-line attribution is best-effort) |
| `reason` | Currently always `phantom_lesson_id` |
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

## Cross-References

- **`plan-marshall:tools-input-validation`** — Owns `scan_lesson_id_tokens` and `verify_lesson_ids_exist` (the single source of truth for lesson-ID detection; this skill never re-implements either function)
- **`plan-marshall:manage-findings`** — Receives the Q-Gate findings (`qgate add`) so the standard Phase 5 triage loop can resolve them (FIX / SUPPRESS / ACCEPT)
- **`plan-marshall:manage-tasks`** — At-write-time validator (companion to this post-hoc sweep); together they cover both the prevention and detection paths for lesson-ID drift
- **Lessons** — The live-anchor discipline enforced here originates in lessons `2026-04-29-10-001` (regex/data drift surfacing as silent green) and `2026-05-03-21-002` (live-anchored test fixtures). See `standards/check-lesson-id-references.md` for the rationale and how to interpret/resolve findings.

## Standards (Load On-Demand)

```
Read standards/check-lesson-id-references.md
```
