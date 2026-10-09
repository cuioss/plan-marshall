# Lessons archive — index

Written by the `ingest` command of the `lessons-routing` epic (RULING 2026-10-09 in `epic.md`). Each
lesson file is a verbatim copy of the corpus file, placed under the directory of its level. Clusters of
duplicates and near-duplicates are recorded here; the lesson files themselves are kept one per id.

Grades follow the `live-blockers` epic's `backlog.md` where that list already graded the subject (the
section is cited); the rest are the orchestrator's own grade. Only the lessons filed to `live-blockers`
and the two stale ones were checked against the code or the ledger at ingest time — the `medium/` and
`low/` grades rest on the lesson text and the backlog's earlier verification.

## Sweep 2026-10-09 — 34 lessons, 6 carry-over rows

### `filed-live-blockers/` — high, filed to the `live-blockers` inbox (9 lessons)

| Message | Lessons | Subject | Owner today |
|---|---|---|---|
| `lessons-routing-001` | `2026-09-29-17-001`, `2026-10-02-10-005`, `2026-10-07-07-001` | Self-review does not converge and re-fires settled finalize steps (backlog § 1.2) | PLAN-LB-22 shipped, #1726 shipped, PLAN-LB-32 staged |
| `lessons-routing-002` | `2026-10-02-10-003`, `2026-10-02-10-004` | Scope-creep guard cannot persist its finding and diffs the wrong base (backlog § 1.7) | PLAN-LB-27 staged |
| `lessons-routing-003` | `2026-10-03-18-001`, `2026-10-07-07-007`, `2026-10-07-07-008` | Review step: stale required bot, unrunnable poll wait, "fixed" posted before the commit (backlog §§ 4.4, 1.5) | PLAN-LB-24 running, PLAN-LB-25 staged |
| `lessons-routing-004` | `2026-10-06-15-001` | Review-bot fleet enrolment of the schema-failing repositories (backlog § 4.5) | PLAN-LB-31 staged |

### `medium/` (16 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-27-07-003`, `2026-10-02-21-003` | Plan advances past the outline with Q-Gate findings pending (two routes to one state) | § 1.17 |
| `2026-09-27-07-004` | Strict handshake fails on other sessions' writes to the main checkout; eased by the shared ledger worktree | § 1.15 |
| `2026-09-27-08-001` | Lessons-housekeeping Step 1 reads the retired `modified_files` field | § 1.12 |
| `2026-09-28-17-001` | `ci checks status` omits a reusable workflow's nested checks | § 2.7 |
| `2026-09-29-17-002` | `affected_files` is never re-synced, so finalize gates under-scope | § 1.13 |
| `2026-10-02-10-002` | Landing gate cannot tell an ejected PR from a queued one | § 1.23 |
| `2026-10-02-10-009`, `2026-10-03-18-003` | Orchestrator-tier test runs: filed under no plan, and each one ends an execute envelope | § 2.9 |
| `2026-10-07-07-002` | A script a plan changed cannot be called by the same plan (stale executor) | § 2.3 |
| `2026-10-07-07-009` | `WORKTREE` dispatch contract says repo-relative, dispatcher sends absolute | § 1.20 |
| `2026-10-02-10-008`, `2026-10-07-07-004` | Dispatch-boundary rows are keyless and record an omitted figure as `0` | not listed (metrics) |
| `2026-10-07-07-003` | `post_run_source_guard` called with an undeclared `--plan-id`, so the guard did not run | not listed |
| `2026-10-07-07-005` | Foreign-repository paths need their own class in the declared footprint | not listed |
| `2026-10-02-21-005` | A re-fire overwrites the earlier firing's step record | not listed |

### `low/` (7 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-27-19-001` | `Module_testing scope` is not named in the phase-4 task-split algorithm (file has no metadata header) | § 5 |
| `2026-10-02-10-007`, `2026-10-02-21-001` | Retrospective counts read-intent paths and rename sources as unrealised | not listed |
| `2026-10-02-21-002` | Execute workflow does not name the `get-deliverable` call | not listed |
| `2026-10-02-21-004` | `display_detail` contract is not enforced | not listed |
| `2026-10-03-18-002` | No script computes the Q-Gate deliverable hashes | § 1.18 |
| `2026-10-07-07-006` | Release and deploy steps planned as leaf steps | § 4.11 |

### `stale/` (2 lessons)

| Lesson | Why |
|---|---|
| `2026-10-02-10-001` | All three proposed actions are marked completed in PLAN-LB-30, shipped as #1722 (`2cb0f8c3f` on `main`). |
| `2026-10-02-21-006` | `live-blockers` `backlog.md` § 5 lists it as already fixed (the R4 worktree block, #1688). Not re-checked here. |

### PLAN-09 (#1652) carry-over rows

Six rows from `inbox/archive/orchestrator-refactor/orchestrator-refactor-001.md`; they were never corpus
lessons, so there is no file per row. Full text and fixtures are in that message.

| Row | Subject | Level | Note |
|---|---|---|---|
| 1 | A payload delivered far below its produced size is truncated, never "small" | medium | retrospective tier selection |
| 2 | Dispatch-boundary records carry the step key and usage; unmeasured is never `0` | medium | same subject as `2026-10-02-10-008` / `2026-10-07-07-004` |
| 3 | A coverage-class step without its tool returns a coverage gap and spends no loop-back | high | filed in `lessons-routing-001` |
| 4 | Excluded-versus-declared outline paths; declared lists reconciled after execute | medium | same subject as `2026-09-29-17-002` |
| 5 | A landing's merge-commit fact comes from the PR merge record, not local HEAD | low | backlog § 1.24 |
| 6 | A reserved never-removed resource has a dedicated refusal on every destructive path | low | backlog § 3.3 |
