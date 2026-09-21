envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T06:02:55Z

component=plan-marshall:manage-lessons
category=improvement
confidence=high
kind_detail=recurrence-observations
source_plan=user-language-and-vocabulary
source_pr=1382

# Five active lessons reproduced in a single run — recurrence sections owed

## Context

This is **not** a proposal for a new lesson. It is a batch of second-or-later observations of five lessons already active in the global corpus, routed to the epic rather than appended directly because on the orchestrated branch corpus mutation belongs to the orchestrator. Each entry below is a `## Recurrence — 2026-09-03 (user-language-and-vocabulary)` section owed to an existing lesson file.

All five were retained by `project:finalize-step-lessons-housekeeping` on 2026-09-02 with the classification "untouched by this plan. No coverage." That was correct — this plan did not touch them. They then all reproduced during the same run.

## Recurrences

### `2026-08-25-09-001` — phase-6-finalize realized-footprint capture

Reproduced live in the retrospective envelope: `manage-references get --plan-id user-language-and-vocabulary --field modified_files` returns `error: field_not_found`. Independently hit by lessons-housekeeping at `22:54:47` ("modified_files field absent from references"). Downstream cost this run: `check-manifest-consistency`, `check-routing-decisions` and `check-outline-vs-shipped` all declare a `--diff-file` flag and had no recorded footprint to read, so the retrospective derived `work/footprint.txt` by hand from `git diff 80da16e30 219da7b1d`.

### `2026-08-25-09-014` — `--measured-diff-size` lacks `nargs='?'`

Reproduced verbatim at the pre-merge barrier: `review_completeness check` rejected with `exit_code=2`, `failure_kind=argparse_rejection`, at `2026-09-03T00:43:12Z`. A live `--help` walk confirms the asymmetry is unchanged — `--measured-diff-size MEASURED_DIFF_SIZE` takes a mandatory value while all eight sibling list flags render as `[--flag [VALUE]]` and each documents "May be supplied bare (no value)".

### `2026-08-25-09-009` — `analyze-logs` `build_count: 0` against daemon-routed builds

Reproduced. The `log-analysis` fragment reports `build_time.build_count: 0` and `total_build_seconds: 0.0`, so the build-time oracle reads *unavailable*. The same fragment's cost rollup records 46 `pyproject_build` calls totalling 2,117,690 ms and 22 `build_server` calls totalling 2,841,770 ms. Daemon-routed builds write no change-ledger row, so the oracle sees none of it.

### `2026-08-25-09-008` — deploy-target's hard-coded `uv run python`

Reproduced at deploy-target. decision.log `2026-09-03T05:39:11Z`: "`uv` is not on PATH in this shell (exit 127), so the documented `uv run python marketplace/targets/generate.py` was run as `.venv/bin/python3 marketplace/targets/generate.py` with identical arguments." The step still depends on an agent noticing the failure and substituting the launcher.

### `2026-09-02-13-005` — `[VERIFY]` emission absent across the finalize lane

Second observation. Zero `[VERIFY]` entries in a 538-entry work log; the top five tags are STATUS 93, SKILL 60, STEP 58, ARTIFACT 30, DISPATCH 19. Verification demonstrably ran: three phase-5 verification steps (`verify:quality-gate`, `verify:module-tests`, `verify:coverage`), four `pre-push-quality-gate` firings and three `ci-verify` firings.

## Note on a sixth

`2026-09-02-08-001` (Sourcery quota refusal unmatched by `refusal_patterns`) also recurred on this PR, but `project:finalize-step-review-retrospective` already recorded it as its second observation at order 990, with the full metric-propagation trace. It is named here for completeness and deliberately **not** re-filed — one observation, one record.

## Proposed action

Append a `## Recurrence — 2026-09-03 (user-language-and-vocabulary)` section to each of the five lesson files, carrying that lesson's paragraph above. Then consider whether five simultaneous recurrences in one run, none with a landed remedy, is itself a scheduling signal for the epic.
