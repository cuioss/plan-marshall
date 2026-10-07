envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T20:56:59Z

component=plan-marshall:manage-architecture
category=bug
title=architecture search --content is case-sensitive with no --ignore-case and double-counts multi-module files
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087

# architecture search --content is case-sensitive with no --ignore-case and double-counts multi-module files

## Context

`architecture search --content` is the sanctioned Grep substitute for dispatched leaves — the project hard rule blocks Bash `grep`/`find` unconditionally, and Grep/Glob were NOT granted to this plan's leaves. It is therefore the ONLY content-sweep mechanism available to a leaf, and residual sweeps depend on it entirely.

It has two verified measurement defects.

## Root cause

**Defect 1 — case-sensitive with no escape hatch.** The full argparse surface is `--content`, `--pattern`, `--category`, `--literal`. There is NO `--ignore-case`/`-i` flag. `--pattern` is a Python regex, so an inline `(?i)` works, but nothing in `--help` says so, and `--literal` (the flag an author reaches for when the pattern has regex metacharacters like `--pr-number`) makes `(?i)` impossible because the pattern is `re.escape`d. So the two things an author most wants — verbatim matching AND case-insensitivity — are mutually exclusive by construction.

**Defect 2 — `count` double-counts.** Searching `alternative to --pr-number` returns `count: 2` with two result rows that are the SAME path (`test/plan-marshall/tools-integration-ci/test_ci_base.py`), listed once under module `default` and once under module `plan-marshall`. A caller reading `count` as "files matched" over-reports by the module-overlap factor. The per-row `match_count` (3) is correct; the top-level `count` is not a file count.

## Proposed action

1. Add `--ignore-case` and make it compose with `--literal` (fold to `re.escape(pattern)` under `re.IGNORECASE`).
2. Either dedupe `results[]` by path, or rename `count` to `match_rows` and add a distinct `files_matched`.
3. Until (1) lands, document the `(?i)` inline form in the `--pattern` help text.

## Evidence

- `architecture search --help` — the flag set is exactly `--content --pattern --category --literal`; no case flag exists.
- `architecture search --content --pattern "alternative to --pr-number"` → `count: 2`, two rows, one file.
- This plan's residual sweeps returned 0 for phrasings that were live in the tree; see the sibling candidate-lesson on scope-vs-claim for the consequence.

## Dedup context for the orchestrator

No global lesson consulted during this plan (21 consulted, 10 heeded) records an `architecture search` measurement defect. Gate 1 dedup was NOT run — `orchestrated: true` routes to this inbox and the orchestrator owns classification.
