# Finalize Output Template

Defines how `phase-6-finalize` renders its final user-facing output as a fixed five-block template: **Headline + Goal + Deliverables + Finalize steps** closed by a one-line **Repository** trailer. The renderer runs as the terminal action of the phase, after `default:archive-plan` returns. It is NOT a configurable step in the `steps` list — it always runs.

The renderer is a pure assembler: it never invents per-step content. Each finalize step authors its own one-line `display_detail` string at `mark-step-done` time; the renderer only concatenates those strings against the configured step order.

## Template Skeleton

```
[TOKEN] PR #{n} -- {N} deliverable(s) shipped, {state summary}

Goal
  {summary}

Deliverables ({N_done}/{N_total})
  [OK]  1. {deliverable 1 title}
  [OK]  2. {deliverable 2 title}

Finalize steps ({N_done}/{N_total} done)
  [OK]  commit-push                       -> {commit_hash}
  [OK]  create-pr                         #{pr_number}
  [OK]  automated-review                  {N} comment(s) resolved (no loop-back)
  [OK]  sonar-roundtrip                   quality gate passed
  [OK]  knowledge-capture                 saved pattern: {pattern_id}
  [OK]  lessons-capture                   {N} lesson(s) recorded ({lesson_ids})
  [OK]  branch-cleanup                    main pulled, branch deleted (local+remote), worktree removed
  [OK]  review-knowledge                  2d/1u/5k of 8
  [OK]  record-metrics                    {duration}s / {tokens} tokens
  [OK]  archive-plan                      -> {archive_path}

Repository: main up-to-date | worktree removed | working tree clean
```

Placeholder glossary:

- `{TOKEN}` — one of `MERGED`, `OPEN`, `LOOP_BACK`, `SKIPPED`, `FAILED` (see rules below)
- `{n}` — PR number, or `n/a` when no PR exists
- `{N}` / `{N_done}` / `{N_total}` — integer counts
- `{commit_hash}` — short hash (7 chars) returned by `commit-push`
- `{archive_path}` — relative path returned by `default:archive-plan`
- `{summary}` — the 2-3 sentence Summary body from `solution_outline.md`, wrapped to ~78 chars with a 2-space indent. When the Summary is missing or empty, the renderer substitutes the literal placeholder `(no summary recorded)`.
- All remaining `{...}` values come verbatim from each step's `display_detail`

## Headline Token Rules

| Token | Condition |
|-------|-----------|
| `[MERGED]` | PR exists and state=merged |
| `[OPEN]` | PR exists and state!=merged |
| `[LOOP_BACK]` | finalize iteration > 1 |
| `[SKIPPED]` | no `default:create-pr` in configured steps list AND no PR exists |
| `[FAILED]` | any required step outcome is failed/missing |

**Precedence** (highest wins): `FAILED` > `LOOP_BACK` > terminal-state tokens (`MERGED` / `OPEN` / `SKIPPED`).

Terminal-state tokens are mutually exclusive: `MERGED` wins over `OPEN`, and `SKIPPED` applies only when both no-PR conditions are true.

## ASCII Icon Rules

Only ASCII icons — no unicode glyphs. Icons are interpreted from the step's `outcome` field:

| Icon | Step outcome |
|------|-------------|
| `[OK]` | outcome == done |
| `[SKIP]` | outcome == skipped |
| `[FAIL]` | outcome == failed or required step missing |

Icons are uppercase, wrapped in literal square brackets. Unknown outcomes render as `[FAIL]`.

## Snapshot Procedure

The snapshot MUST run BEFORE `default:archive-plan`, because archive moves `.plan/plans/{plan_id}/` to `.plan/archived-plans/{date}-{plan_id}/` and invalidates subsequent `manage-status read` calls against the live path.

Capture the following into in-memory state (no work file is written):

1. **phase_steps map** — step outcomes and display_detail strings.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
     --plan-id {plan_id}
   ```

   Extract `metadata.phase_steps["6-finalize"]`. This is a dict of `{step_name: {outcome, display_detail}}`.

2. **Deliverables list** — from the solution outline.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage_solution_outline read \
     --plan-id {plan_id}
   ```

   Capture the ordered list of deliverable titles (and per-deliverable completion state if available).

3. **Configured step order** — the order steps should appear in the rendered block.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage_config plan phase-6-finalize get \
     --plan-id {plan_id} --field steps
   ```

   Capture the ordered `steps` list verbatim.

4. **PR state + number** — via the CI abstraction (never direct `gh`/`glab`).

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view \
     --project-dir {main_checkout}
   ```

   Capture `state` and `number`. This call may return an error when no PR exists for the branch; treat as `state=n/a, number=n/a`.

5. **Repository state** — branch name and porcelain status for the trailer.

   ```bash
   git -C {main_checkout} branch --show-current
   ```

   ```bash
   git -C {main_checkout} status --porcelain
   ```

   Capture current branch name and the raw porcelain output (empty string == clean).

6. **Solution outline Summary** — the 2-3 sentence Summary body that feeds the Goal block.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
     --plan-id {plan_id} --section summary
   ```

   Extract the `content` field on success. On `section_not_found` or empty content, store the sentinel value `None` — the emission procedure substitutes the defensive placeholder. This read MUST happen BEFORE `default:archive-plan` runs, because archive moves `solution_outline.md` into the archived-plans directory.

7. **Plan short_description** — the compact label used by the phase-6-finalize terminal `done` emission. Extracted from the live `status.json` before archive moves it.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
     --plan-id {plan_id}
   ```

   Extract `plan.short_description` (or `status.metadata.short_description`, whichever field is populated by `phase-1-init`). Store the raw string, or `None` when the field is absent/empty. The emission procedure hands this value to `set_terminal_title.py --plan-label` verbatim; the script clamps and rejects malformed values on its side.

Keep this snapshot in model context. It is passed to the emission procedure AFTER `default:archive-plan` returns.

## Emission Procedure

Invoked after `default:archive-plan` completes. Inputs: the snapshot from above plus `archive_path` returned by archive-plan.

### 1. Resolve headline token

Walk the precedence chain:

1. If any configured step's `outcome` is `failed`, any required step (per `required-steps.md`) is missing from `phase_steps`, or any configured step's `display_detail` is missing or empty -> `[FAILED]`. A missing/empty `display_detail` violates the interface contract defined in `SKILL.md` and surfaces as `<missing display_detail>` in the step row.
2. Else if `finalize_iteration > 1` -> `[LOOP_BACK]`.
3. Else if PR `state == merged` -> `[MERGED]`.
4. Else if PR exists (any other state) -> `[OPEN]`.
5. Else if `default:create-pr` is NOT in configured `steps` list AND no PR exists -> `[SKIPPED]`.
6. Otherwise default to `[OPEN]` (PR was configured but `ci pr view` returned `n/a` — treat as degraded).

### 2. Build headline

```
{TOKEN} PR #{n} -- {N} deliverable(s) shipped, {state summary}
```

- `{n}` = PR number or `n/a`.
- `{N}` = total deliverables count from the outline.
- `{state summary}` = short free-text summary authored by the renderer from step outcomes (e.g., `all steps done`, `1 step failed`, `loop-back iteration 2`).

No commit hashes appear in the headline — they live inline with the `commit-push` row.

### 3. Build Goal block

Header literal: `Goal` (no trailing colon). Follow the literal `Goal` line with a single blank line, then the Summary text wrapped to ~78 chars with a 2-space indent on every wrapped line.

Wrap implementation guidance: use Python's `textwrap.fill(summary, width=78, initial_indent='  ', subsequent_indent='  ', break_long_words=False, break_on_hyphens=False)` or the equivalent — preserve URLs and long identifiers intact rather than splitting mid-token.

Defensive fallback: when the snapshot captured `None` or an empty string for Summary (sentinel emitted by the Snapshot Procedure when `section_not_found` or empty content is returned), emit the literal placeholder so the block remains valid:

```
Goal
  (no summary recorded)
```

ASCII only — no unicode glyphs, no emoji, no box-drawing characters in the Goal block. This matches the rest of the template's aesthetic.

### 4. Build deliverables block

Header: `Deliverables ({N_done}/{N_total})`

One row per deliverable in outline order:

```
  {icon}  {n}. {deliverable title}
```

Icon resolution:

- If the solution outline tracks per-deliverable outcomes and all affiliated steps succeeded -> `[OK]`.
- If any affiliated step failed -> `[FAIL]`.
- If all affiliated steps are skipped -> `[SKIP]`.
- When no per-deliverable outcome is available, fall back to `[OK]`.

Deliverable numbering starts at `1.` and pads width to accommodate up to 99 deliverables (`" 1."` vs `"10."`).

### 5. Build finalize steps block

Header: `Finalize steps ({N_done}/{N_total} done)` where `N_total` = count of configured steps and `N_done` = count with `outcome == done`.

Iterate the configured `steps` list in order. For each step, emit:

```
  {icon}  {step_name_padded}  {display_detail}
```

- `{step_name_padded}` = step name left-justified to a fixed column width of **33 characters** (pad with spaces, no truncation). Long step names overflow and push the detail column one space to the right — accepted.
- `{display_detail}` = the verbatim detail string authored by the step. If `display_detail` is missing or empty, emit the literal placeholder `<missing display_detail>` (this is a contract violation and should be surfaced).
- Two spaces separate the icon from the step name; two spaces separate the padded name from the detail.

### 6. Build repository trailer

One line, joined by ` | ` (space pipe space):

```
Repository: {main state} | {worktree token?} | {working tree state}
```

See "Repository Trailer Rules" below.

### 7. Emit

Print the five blocks separated by blank lines:

```
{headline}

{goal block}

{deliverables block}

{finalize steps block}

{repository trailer}
```

No trailing whitespace. No ANSI color codes. Plain text only.

## display_detail Contract for Step Authors

Every finalize step — built-in (`default:*`), project (`project:*`), and fully-qualified skill — MUST pass `--display-detail "{one-line}"` to its `mark-step-done` invocation. This is required, not optional. There is NO fallback to the raw step name.

Detail string rules:

- **Max 80 characters** (softer limits encouraged; the renderer does not truncate)
- **No trailing period**
- **No embedded newlines** — single line only
- **Plain ASCII** — no unicode glyphs
- **Concrete and user-facing** — describe what the step did, not how

### Concrete Examples per Built-in Step

| Step | Outcome scenario | display_detail |
|------|------------------|----------------|
| `commit-push` | Changes committed and pushed | `-> a1b2c3d` |
| `commit-push` | No changes to commit | `no changes` |
| `create-pr` | New PR created | `#212` |
| `create-pr` | Existing PR re-used | `existing PR #212` |
| `create-pr` | Skipped | `skipped` |
| `automated-review` | Bot comments resolved on first pass | `3 comment(s) resolved (no loop-back)` |
| `automated-review` | Skipped (no PR) | `skipped` |
| `automated-review` | Loop-back fixes applied | `loop-back iteration 2` |
| `sonar-roundtrip` | Quality gate passed | `quality gate passed` |
| `sonar-roundtrip` | Quality gate failed | `quality gate failed` |
| `sonar-roundtrip` | Skipped | `skipped` |
| `knowledge-capture` | New pattern saved | `saved pattern: auth-handshake` |
| `knowledge-capture` | Nothing new captured | `no new pattern saved` |
| `lessons-capture` | Lessons recorded | `2 lesson(s) recorded (2026-04-17-006, 2026-04-17-007)` |
| `lessons-capture` | Nothing captured | `no lessons recorded` |
| `branch-cleanup` | PR mode full cleanup | `main pulled, branch deleted (local+remote), worktree removed` |
| `branch-cleanup` | Local-only mode | `local-only: switched to main` |
| `branch-cleanup` | Declined by user | `declined by user` |
| `review-knowledge` | Actions applied | `2d/1u/5k of 8` |
| `review-knowledge` | Nothing to review | `nothing to review (1 lesson, 32 memories)` |
| `review-knowledge` | User declined | `user declined review` |
| `record-metrics` | Metrics recorded | `{duration}s / {tokens} tokens` |
| `archive-plan` | Archived successfully | `-> .plan/archived-plans/2026-04-17-jwt-auth/` |
| `validation` | All required steps done | `all required steps done` |
| `validation` | N checks passed | `{N} validation check(s) passed` |

## Repository Trailer Rules

The trailer summarises on-disk state so the user does not need to run `git status` / `ci pr view` after finalize.

Tokens (joined by ` | `):

1. **Main branch state**
   - If current branch == `main` AND `git status --porcelain` on main is empty -> `main up-to-date`
   - If current branch != `main` -> `main NOT up-to-date`
   - If on main but porcelain is non-empty -> `working tree dirty`

2. **Worktree token** (conditional — drop entirely on no-worktree path)
   - If the plan used a worktree AND `branch-cleanup` removed it -> `worktree removed`
   - If the plan used a worktree AND it was NOT removed -> `worktree retained`
   - If the plan did NOT use a worktree -> omit the token (do not emit an empty segment)

3. **Working tree state**
   - If porcelain output is empty -> `working tree clean`
   - Otherwise -> `working tree: {N} uncommitted files` (count lines of porcelain output)

Join with ` | ` (literal: space, pipe, space). Examples:

- Full worktree path (merged): `Repository: main up-to-date | worktree removed | working tree clean`
- No-worktree path: `Repository: main up-to-date | working tree clean`
- Degraded: `Repository: main NOT up-to-date | worktree retained | working tree: 3 uncommitted files`

## Integration Notes

- The renderer is invoked by `phase-6-finalize/SKILL.md` as the final step AFTER `default:archive-plan` returns. It is NOT listed in the configurable `steps`; it always runs.
- The snapshot is captured BEFORE `default:archive-plan` because archive moves `status.json` and invalidates `manage-status read` calls against the live plan directory.
- The snapshot is held in model context (no work file is written on disk).
- The renderer consumes only the in-memory snapshot plus the `archive_path` returned by archive-plan. It performs no additional `manage-status`/`manage-solution-outline`/`ci pr view` reads.
- Missing `display_detail` entries surface as the literal placeholder `<missing display_detail>` to aid debugging — they also contribute to the `[FAILED]` precedence decision when combined with a failed outcome.
