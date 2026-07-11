# Finalize Output Template

Defines how `phase-6-finalize` renders its final user-facing output. The default mode emits a fixed five-block template: **Headline + Goal + Deliverables + Finalize steps** closed by a one-line **Repository** trailer. The renderer runs as the terminal action of the phase, after `default:archive-plan` returns. It is NOT a configurable step in the `steps` list — it always runs.

The renderer is a pure assembler: it never invents per-step content. Each finalize step authors its own one-line `display_detail` string at `mark-step-done` time; the renderer only concatenates those strings against the configured step order.

When `finalize-step-print-phase-breakdown` is present in `manifest.phase_6.steps` AND its outcome is `done`, the renderer enters **Phase Breakdown supplement mode**: the verbatim Phase Breakdown table content captured from `metrics.md` is appended as an additional section AFTER the Finalize-steps block. Every step row in the Finalize-steps block (including `record-metrics`) emits unchanged; the breakdown supplements the per-step list rather than substituting for any row. All other blocks (Headline, Goal, Deliverables, Repository trailer) emit unchanged as well. See `## Phase Breakdown Supplement` below for the full toggle, snapshot read, and append emission rule.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Template Skeleton

```text
[TOKEN] PR #{n} -- {N} deliverable(s) shipped, {state summary}

Goal
  {summary}

Deliverables ({N_done}/{N_total})
  [OK]  1. {deliverable 1 title}
  [OK]  2. {deliverable 2 title}

Finalize steps ({N_done}/{N_total} done)
  [OK]  push                              pushed {branch}
  [OK]  create-pr                         #{pr_number}
  [OK]  automated-review                  {N} comment(s) resolved (no loop-back)
  [OK]  sonar-roundtrip                   quality gate passed
  [OK]  lessons-capture                   {N} lesson(s) recorded ({lesson_ids})
  [OK]  branch-cleanup                    main pulled, branch deleted (local+remote), worktree removed
  [OK]  record-metrics                    {total_duration_formatted} / {total_tokens_formatted} tokens
  [OK]  archive-plan                      -> {archive_path}

Repository: main up-to-date | worktree removed | working tree clean
```

### Phase Breakdown supplement skeleton

When the supplement is active (see `## Phase Breakdown Supplement` below), the verbatim Phase Breakdown table content captured from `metrics.md` is appended as an additional section AFTER the Finalize-steps block. Every step row in the Finalize-steps block — including the `record-metrics` row — emits unchanged.

```text
[TOKEN] PR #{n} -- {N} deliverable(s) shipped, {state summary}

Goal
  {summary}

Deliverables ({N_done}/{N_total})
  [OK]  1. {deliverable 1 title}

Finalize steps ({N_done}/{N_total} done)
  [OK]  push                              pushed {branch}
  [OK]  create-pr                         #{pr_number}
  [OK]  automated-review                  {N} comment(s) resolved (no loop-back)
  [OK]  sonar-roundtrip                   quality gate passed
  [OK]  lessons-capture                   {N} lesson(s) recorded ({lesson_ids})
  [OK]  branch-cleanup                    main pulled, branch deleted (local+remote), worktree removed
  [OK]  record-metrics                    {total_duration_formatted} / {total_tokens_formatted} tokens
  [OK]  archive-plan                      -> {archive_path}

Phase Breakdown

## Phase Breakdown

| Phase | Worked | Reported (wall) | Idle | Tokens | Tool Uses |
|-------|--------|-----------------|------|--------|-----------|
| 1-init | 2m10s | 2m41s | 31s | 53,719 | 29 |
| 2-refine | 6m05s | 8m41s | 2m36s | - | - |
| ... | ... | ... | ... | ... | ... |
| **Total** | **1h22m** | **1h46m** | **24m** | **599,089** | **...** |

Repository: main up-to-date | worktree removed | working tree clean
```

**Reading the skeleton — the supplement block has two adjacent headers and they come from different sources.** The plain-text `Phase Breakdown` line (third from the bottom in the supplement-active sample) is the **literal one-line header the renderer emits**. The next `## Phase Breakdown` line is the **first line of the verbatim content** captured from `work/phase-breakdown-output.txt` (which already begins with that markdown heading and ends with a single trailing newline). The renderer emits the plain-text header itself; it does NOT add or modify the `## Phase Breakdown` that comes from the captured file. See `## Phase Breakdown Supplement` below for the toggle activation rules and the authoritative description of this two-header structure.

Placeholder glossary:

- `{TOKEN}` — one of `MERGED`, `OPEN`, `LOOP_BACK`, `SKIPPED`, `FAILED` (see rules below)
- `{n}` — PR number, or `n/a` when no PR exists
- `{N}` / `{N_done}` / `{N_total}` — integer counts
- `{branch}` — the feature branch name pushed by `push`
- `{archive_path}` — relative path returned by `default:archive-plan`
- `{summary}` — the 2-3 sentence Summary body from `solution_outline.md`, wrapped to ~78 chars with a 2-space indent. When the Summary is missing or empty, the renderer substitutes the literal placeholder `(no summary recorded)`.
- All remaining `{...}` values come verbatim from each step's `display_detail`

## Headline Token Rules

| Token | Condition |
|-------|-----------|
| `[MERGED]` | PR exists and state=merged |
| `[OPEN]` | PR exists and state!=merged |
| `[LOOP_BACK]` | finalize iteration > 1 |
| `[SKIPPED]` | no `create-pr` in `manifest.phase_6.steps` AND no PR exists |
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
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
     --plan-id {plan_id}
   ```

   Extract `metadata.phase_steps["6-finalize"]`. This is a dict of `{step_name: {outcome, display_detail}}`.

2. **Deliverables list** — from the solution outline.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage_solution_outline read \
     --plan-id {plan_id}
   ```

   Capture the ordered list of deliverable titles (and per-deliverable completion state if available).

3. **Configured step order** — the order steps should appear in the rendered block. Read from the per-plan execution manifest:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest read \
     --plan-id {plan_id}
   ```

   Capture `phase_6.steps` (a list of bare step IDs) verbatim — this is the renderer's authoritative ordering. The renderer prepends `default:` only when looking up dispatch-table records; the rendered step name is the bare ID as it appears in the manifest. Do NOT read the legacy `marshal.json` `steps` field; it is no longer authoritative.

4. **PR state + number** — via the CI abstraction (never direct `gh`/`glab`).

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view \
     --plan-id {plan_id}
   ```

   The `--plan-id` form auto-resolves the active worktree (or falls back to the main checkout once the plan's worktree has been removed). Use `--project-dir {main_checkout}` instead if an explicit override is required (the two flags are mutually exclusive). Capture `state` and `number`. This call may return an error when no PR exists for the branch; treat as `state=n/a, number=n/a`.

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

7. **Phase Breakdown override content** — the captured stdout produced by the optional `finalize-step-print-phase-breakdown` step. The step (when present in `manifest.phase_6.steps`) writes the verbatim `## Phase Breakdown` section content to `work/phase-breakdown-output.txt` for this read.

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
     --plan-id {plan_id} --file work/phase-breakdown-output.txt
   ```

   When `exists: true`, read the content:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
     --plan-id {plan_id} --file work/phase-breakdown-output.txt
   ```

   Extract the file content. When the file does not exist (the step was not configured, was skipped, or failed), store sentinel `None` — the override does NOT activate and emission falls back to the default Finalize-steps block. This read MUST happen BEFORE `default:archive-plan` runs, because archive moves the entire plan directory (including `work/`) into the archived-plans tree. The producer of this file is documented in `finalize-step-print-phase-breakdown/SKILL.md` (cross-deliverable contract for the path string).

Keep this snapshot in model context. It is passed to the emission procedure AFTER `default:archive-plan` returns.

## Phase Breakdown Supplement

The renderer supports an opt-in **Phase Breakdown supplement mode** that appends the captured Phase Breakdown table from `metrics.md` as an additional section AFTER the Finalize-steps block. The supplement is intended for users who want the compact per-phase metrics breakdown alongside the per-step `[OK]` list — the breakdown supplements the per-step list rather than substituting for any row.

**Toggle activation**: the supplement activates when BOTH conditions hold:

1. `finalize-step-print-phase-breakdown` (or its fully-qualified marketplace notation) is present in `manifest.phase_6.steps`.
2. The captured `phase_breakdown_override_content` from Snapshot Procedure step 7 above is non-`None` (i.e. `work/phase-breakdown-output.txt` existed and was read successfully).

When EITHER condition fails, the supplement is inactive and emission proceeds without the appended breakdown section. There is no error path for "step configured but no content captured" — the renderer fails open so the finalize summary always emits.

**Append emission**: when the toggle is active, after the per-step iteration in Emission Procedure step 5 completes (every configured step row including `record-metrics` has emitted unchanged), the renderer appends an additional section consisting of a blank line, the literal one-line header `Phase Breakdown`, a blank line, then the verbatim captured content (which already begins with `## Phase Breakdown` and ends with a single trailing newline). The Repository trailer (step 6 emission) follows after the appended section, separated by a blank line.

**Unchanged blocks**: the supplement mode does NOT alter any step row in the Finalize-steps block. Every step row (`push`, `create-pr`, `automated-review`, `sonar-roundtrip`, `lessons-capture`, `branch-cleanup`, `record-metrics`, `archive-plan`, etc.) emits identically to default mode. The Headline (step 1-2), Goal (step 3), Deliverables (step 4), and Repository trailer (step 6) blocks emit identically in both modes. The supplement adds a new section between the Finalize-steps block and the Repository trailer; it never replaces existing content.

## Emission Procedure

Invoked after `default:archive-plan` completes. Inputs: the snapshot from above plus `archive_path` returned by archive-plan.

### 1. Resolve headline token

Walk the precedence chain:

1. If any manifest step's `outcome` is `failed` (including the dispatcher-recorded `failed` from a per-agent timeout), any required step (per `required-steps.md`) that is also in `manifest.phase_6.steps` is missing from `phase_steps`, or any manifest step's `display_detail` is missing or empty -> `[FAILED]`. A missing/empty `display_detail` violates the interface contract defined in `SKILL.md` and surfaces as `<missing display_detail>` in the step row. Required steps that are NOT in the manifest for this plan are not enforced — they cannot trigger `[FAILED]`.
2. Else if `finalize_iteration > 1` -> `[LOOP_BACK]`.
3. Else if PR `state == merged` -> `[MERGED]`.
4. Else if PR exists (any other state) -> `[OPEN]`.
5. Else if `create-pr` is NOT in `manifest.phase_6.steps` AND no PR exists -> `[SKIPPED]`.
6. Otherwise default to `[OPEN]` (PR was in the manifest but `ci pr view` returned `n/a` — treat as degraded).

### 2. Build headline

```text
{TOKEN} PR #{n} -- {N} deliverable(s) shipped, {state summary}
```

- `{n}` = PR number or `n/a`.
- `{N}` = total deliverables count from the outline.
- `{state summary}` = short free-text summary authored by the renderer from step outcomes (e.g., `all steps done`, `1 step failed`, `loop-back iteration 2`).

No commit hashes appear in the headline — per-step outcomes live inline with their step rows.

### 3. Build Goal block

Header literal: `Goal` (no trailing colon). Follow the literal `Goal` line with a single blank line, then the Summary text wrapped to ~78 chars with a 2-space indent on every wrapped line.

Wrap implementation guidance: use Python's `textwrap.fill(summary, width=78, initial_indent='  ', subsequent_indent='  ', break_long_words=False, break_on_hyphens=False)` or the equivalent — preserve URLs and long identifiers intact rather than splitting mid-token.

Defensive fallback: when the snapshot captured `None` or an empty string for Summary (sentinel emitted by the Snapshot Procedure when `section_not_found` or empty content is returned), emit the literal placeholder so the block remains valid:

```text
Goal
  (no summary recorded)
```

ASCII only — no unicode glyphs, no emoji, no box-drawing characters in the Goal block. This matches the rest of the template's aesthetic.

### 4. Build deliverables block

Header: `Deliverables ({N_done}/{N_total})`

One row per deliverable in outline order:

```text
  {icon}  {n}. {deliverable title}
```

Icon resolution:

- If the solution outline tracks per-deliverable outcomes and all affiliated steps succeeded -> `[OK]`.
- If any affiliated step failed -> `[FAIL]`.
- If all affiliated steps are skipped -> `[SKIP]`.
- When no per-deliverable outcome is available, fall back to `[OK]`.

Deliverable numbering starts at `1.` and pads width to accommodate up to 99 deliverables (`" 1."` vs `"10."`).

### 5. Build finalize steps block (with optional appended `Phase Breakdown` supplement)

Header: `Finalize steps ({N_done}/{N_total} done)` where `N_total` = count of steps in `manifest.phase_6.steps` and `N_done` = count with `outcome == done`.

Iterate the manifest `phase_6.steps` list in order. For each step, look the step entry up in the `phase_steps` map (captured in Snapshot Procedure step 1) using the **exact-then-strip-prefix lookup rule**:

1. Attempt an exact match against the manifest step ID (e.g. `default:pre-submission-self-review`). If found, use that record.
2. If the exact match misses AND the manifest step ID begins with `project:` or `default:`, strip the prefix and retry the lookup against the bare suffix (e.g. `pre-submission-self-review` or `push`). If found, use that record.
3. Only if BOTH lookups miss does the renderer treat the entry as a missing record — emit `<missing display_detail>` for the detail column and surface the row in the `[FAILED]` precedence decision (Emission Procedure step 1).

The strip-prefix retry is a **transitional defense** against legacy `mark-step-done` call sites that record under bare step names while the manifest carries the canonical prefixed form. The manifest-ID spelling is the canonical form (see `## display_detail Contract for Step Authors` below); step authors MUST record under the canonical manifest ID. The strip-prefix retry exists so a future drift between manifest and recorded keys surfaces as a recoverable lookup rather than a false `<missing display_detail>` row.

Then emit:

```text
  {icon}  {step_name_padded}  {display_detail}
```

- `{step_name_padded}` = step name left-justified to a fixed column width of **33 characters** (pad with spaces, no truncation). The padded name is the **manifest step ID as written** (do NOT substitute the bare suffix used to resolve the lookup — the manifest spelling is the authoritative display). Long step names overflow and push the detail column one space to the right — accepted.
- `{display_detail}` = the verbatim detail string authored by the step. If `display_detail` is missing or empty after BOTH lookups miss, emit the literal placeholder `<missing display_detail>` (this is a contract violation and should be surfaced).
- Two spaces separate the icon from the step name; two spaces separate the padded name from the detail.

Every step row — including `record-metrics` — emits unchanged. The renderer does NOT substitute or skip any row inside the Finalize-steps block.

<!-- self-review: keep phase_breakdown_override_content -->

> **Renderer reimplementation note**: any future renderer reimplementation MUST preserve the exact-then-strip-prefix lookup contract above. A reimplementation that only attempts the exact match silently re-introduces the failure mode where manifest entry IDs vs `phase_steps` recorded keys diverge by a `project:` prefix, the renderer emits `<missing display_detail>`, and the `[FAILED]` precedence chain trips even though every step actually succeeded.


**Appended `Phase Breakdown` supplement**: after the per-step iteration completes, if the supplement toggle is active (see `## Phase Breakdown Supplement` above for the toggle activation conditions and the verbatim emission shape of `phase_breakdown_override_content` — the single source of truth for both), append the supplement section as documented there. The Repository trailer (step 6 emission) then follows after the appended section, separated by a blank line per the standard block separator (Emission Procedure step 7).

### 6. Build repository trailer

One line, joined by ` | ` (space pipe space):

```text
Repository: {main state} | {worktree token?} | {working tree state}
```

See "Repository Trailer Rules" below.

### 7. Emit

Print the five blocks separated by blank lines:

```text
{headline}

{goal block}

{deliverables block}

{finalize steps block}

{repository trailer}
```

No trailing whitespace. No ANSI color codes. Plain text only.

## display_detail Contract for Step Authors

Every finalize step — built-in (`default:*`), project (`project:*`), and fully-qualified skill — MUST pass `--display-detail "{one-line}"` to its `mark-step-done` invocation. This is required, not optional. There is NO fallback to the raw step name.

**Canonical step-ID spelling**: the `--step` argument MUST use the manifest-entry-ID spelling (`default:pre-submission-self-review`, not the bare `pre-submission-self-review`; `default:push` is normalized by `mark-step-done` to the bare `push` form used in `phase_steps`). The renderer's exact-then-strip-prefix lookup (Emission Procedure step 5 above) is a transitional defense against legacy call sites, not a license to drift — record under the canonical manifest ID so the exact-match branch wins and the strip-prefix retry stays dormant.

Detail string rules:

- **Max 80 characters** (softer limits encouraged; the renderer does not truncate)
- **No trailing period**
- **No embedded newlines** — single line only
- **Plain ASCII** — no unicode glyphs
- **Concrete and user-facing** — describe what the step did, not how

### `commit_message` Step-Return Contract (mutates_source steps)

A finalize step that declares `mutates_source: true` in its frontmatter MAY return a `commit_message` element in its return TOON — the conventional-commit subject line the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) uses when committing the step's worktree edits. The field is **optional**: when the step omits it (or returns no edits), the dispatcher derives the fallback `chore(finalize): apply {step-name} changes`. Read-only (`mutates_source: false`) steps never reach the instrumentation and MUST NOT return a `commit_message`.

The field is one element of the same return TOON that carries `status` and `display_detail`:

```toon
status: done
display_detail: "{one-line}"
commit_message: "chore(simplify): collapse accidental complexity in {plan_id}"
```

The dispatcher owns the commit; the step authors only the message. The same single-line / plain-ASCII discipline as `display_detail` applies to `commit_message`.

### Concrete Examples per Built-in Step

| Step | Outcome scenario | display_detail |
|------|------------------|----------------|
| `push` | Branch pushed | `pushed feature/jwt-auth` |
| `finalize-step-simplify` | Edits applied | `Simplify: 2 edits, 0 findings` |
| `create-pr` | New PR created | `#212` |
| `create-pr` | Existing PR re-used | `existing PR #212` |
| `create-pr` | Skipped | `skipped` |
| `automated-review` | Bot comments resolved on first pass | `3 comment(s) resolved (no loop-back)` |
| `automated-review` | Skipped (no PR) | `skipped` |
| `automated-review` | Loop-back fixes applied | `loop-back iteration 2` |
| `sonar-roundtrip` | Quality gate passed | `quality gate passed` |
| `sonar-roundtrip` | Quality gate failed | `quality gate failed` |
| `sonar-roundtrip` | Skipped | `skipped` |
| `lessons-capture` | Lessons recorded | `2 lesson(s) recorded (2026-04-17-006, 2026-04-17-007)` |
| `lessons-capture` | Nothing captured | `no lessons recorded` |
| `branch-cleanup` | PR mode full cleanup | `main pulled, branch deleted (local+remote), worktree removed` |
| `branch-cleanup` | Local-only mode | `local-only: switched to main` |
| `branch-cleanup` | Declined by user | `declined by user` |
| `record-metrics` | Metrics recorded | `{total_duration_formatted} / {total_tokens_formatted} tokens` (e.g. `1h46m / 599K tokens`) |
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
