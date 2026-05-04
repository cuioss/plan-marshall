# Check: Lesson-ID References in Plan Tasks

This standard documents the rationale for the `plan-doctor` lesson-ID reference scan, how it interprets findings, and how to resolve them.

## Why this check exists

Two lessons drive it.

### Lesson `2026-04-29-10-001` — regex/data drift surfacing as silent green

A canonical identifier regex (`LESSON_ID_RE`, `PLAN_ID_RE`, etc.) can drift from the on-disk identifier convention without any test failing. When that happens, scanners and validators that depend on the regex silently produce "no matches" or "all valid" output even though every real ID has changed shape. The fix is **runtime live anchoring**: every scanner that depends on a canonical regex MUST re-validate the regex against actual repo data on first use per process and fail loudly when the regex matches none of the live data.

`plan-doctor` enforces this discipline by routing every scan through `tools-input-validation.scan_lesson_id_tokens`, which calls `verify_lesson_id_regex_against_inventory()` on first use. If the live `manage-lessons list` inventory contains IDs but none match `LESSON_ID_RE`, the scan aborts with `LessonRegexAnchoringError` — surfaced as the `lesson_regex_anchored_to_drifted_inventory` error code.

### Lesson `2026-05-03-21-002` — live-anchored test fixtures

Closely related: test fixtures that hand-type IDs (rather than copy-pasting from real `manage-lessons list` output) silently encode the *test author's idea* of the ID shape rather than the actual on-disk shape. The test then proves the regex matches the test author's idea, not reality. `plan-doctor`'s test suite (`test/plan-marshall/plan-doctor/test_plan_doctor.py`) follows the same convention as `test_lesson_id_scanner.py`: every fixture lesson ID is sourced from real inventory output.

The runtime check (`scan_lesson_id_tokens`) and the fixture discipline (test-time) together guarantee that a regex/data drift surfaces as a hard test failure or a runtime `LessonRegexAnchoringError` — never as a green "no findings" report.

## What the check does

For every TASK-*.json file under the targeted plan(s):

1. Parse the file as JSON (skip silently when parse fails — counted as `unreadable`, not `checked`).
2. Concatenate `title` + `description`.
3. Call `scan_lesson_id_tokens(text)` to find every embedded `YYYY-MM-DD-HH-N+` token.
4. Call `verify_lesson_ids_exist(tokens)` to check each token against the live inventory.
5. Emit a Q-Gate finding (phase `5-execute`, source `qgate`, type `bug`, severity `warning`) for every token that resolves to `False`.

The check is intentionally narrow — it does not validate plan IDs, hash IDs, component notations, or any other identifier shape. Each of those will get its own check skill if needed. Keeping `plan-doctor` focused on lesson IDs means the failure mode is unambiguous: every finding means *that exact lesson was renamed, deleted, or never existed*.

## How to interpret findings

A finding shaped like:

```toon
plan_id: my-plan
task_file: TASK-007.json
line: 1
token: 2026-05-03-21-002
reason: phantom_lesson_id
```

means "TASK-007.json (somewhere in `title` or `description`) references the lesson ID `2026-05-03-21-002`, but that ID is not in the current `manage-lessons list` inventory". There are three normal ways this happens:

| Cause | Resolution |
|-------|------------|
| The lesson ID was wrong from the start (typo, hallucinated date, copy-paste from a non-canonical source). | **FIX** — edit the TASK file via `manage-tasks update` to point at the correct lesson, or remove the reference. |
| The lesson was deleted intentionally (its content is no longer relevant). | **FIX** — remove the reference; the task description should not document a deleted lesson. |
| The lesson was renamed (e.g., as part of a stub-to-canonical merge). | **FIX** — update the reference to the new canonical ID. |

There is currently no scenario where `SUPPRESS` or `ACCEPT` is appropriate, because every phantom reference is a real data-integrity defect: someone reading the task who tries to look up the lesson will get an empty result and lose context.

## How to resolve findings

`plan-doctor` writes findings to the standard Q-Gate store, so the standard Phase 5 triage loop (Step 11 of `plan-marshall:phase-5-execute`) handles them. The expected workflow:

1. Run `plan-doctor scan --plan-id <id>` (or `--all` periodically).
2. For each finding, edit the offending TASK file via `manage-tasks update` to fix or remove the reference.
3. Re-run `plan-doctor scan` to confirm `findings_count == 0`.
4. Resolve the Q-Gate findings via `manage-findings qgate resolve` once the underlying file is fixed.

When new TASK files are written via `manage-tasks add` / `manage-tasks update`, the at-write-time validator added in the companion task (TASK-3) catches these references at the source — `plan-doctor` is the safety net for files that landed before the at-write check existed (or files edited outside `manage-tasks`, which should be rare).

## Failure modes

The scan can also fail fatally when the live inventory itself is unhealthy:

| Error code | Cause | What to do |
|------------|-------|------------|
| `lesson_inventory_unavailable` | `manage-lessons list` exited non-zero, returned unparseable output, or could not be invoked. | Investigate `manage-lessons list` directly — until it returns a valid inventory, no lesson-ID scan is meaningful. Do NOT bypass the check. |
| `lesson_regex_anchored_to_drifted_inventory` | The live inventory contains lesson IDs but none match `LESSON_ID_RE`. | The canonical regex has drifted from reality. Either fix `LESSON_ID_RE` in `tools-input-validation/scripts/input_validation.py` to match the actual on-disk shape, or rename the offending lessons to match the canonical shape. Both `plan-doctor` and every other scanner that depends on the regex are wrong until this is fixed. |

These failures intentionally do not silently degrade to "no findings". The whole point of the live-anchor discipline is that a broken anchor is louder than a missing finding.
