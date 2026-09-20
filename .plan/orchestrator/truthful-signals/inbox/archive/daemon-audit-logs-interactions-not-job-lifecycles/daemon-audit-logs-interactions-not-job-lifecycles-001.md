envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=landing
created=2026-07-28T15:46:34Z

## What landed

**PR #1037** — `fix(manage-build-server): stop conflating request status with job state`
Branch `feature/daemon-audit-logs-interactions-not-job-lifecycles`, 3 commits, 8 files, +913/-54.

The marshalld interaction-audit log conflated two different questions under one
`outcome` field. A `submit` recorded `outcome: queued` forever — truthful about the
*request*, unanswerable about the *job*. The operator surface could not distinguish a
completed build from an abandoned one.

Shipped:

- **Split the vocabulary.** The audit log now carries two explicitly discriminated
  record kinds: `kind='interaction'` (one per dispatched request, field renamed
  `outcome` → `request_status`) and `kind='job_fate'` (one per job terminalization,
  field `fate` from the wire vocabulary `success|failure|timeout|killed`).
  `request_status` is deliberately NOT called `outcome` — it says how the *request*
  was answered and nothing about how the *job* ended.
- **Fail-closed third value (ADR-009).** A fate the daemon cannot substantiate is
  written as `unknown` — never a terminal status it did not observe, never the
  request-scoped `queued`. The two genuinely undeterminable conditions are a journal
  entry already GC'd past its 3600 s window, and a daemon that died and never came
  back (so restart replay never ran).
- **Emission, not read-time join.** Fate is emitted into the 7-day audit store at the
  daemon's two terminalization seams (`_execute` after `record_result`, and per id
  returned by `replay_on_restart` in `serve`), rather than joined against the journal
  at read time. Rationale in the module docstring: journal entries are GC'd at 3600 s
  while audit rows live 7 days, so a join could answer only for a row's first hour.
- **`logs` labels the record kind** so an interaction row is unmistakable to the reader.
- **Best-effort and secrets discipline both preserved.** `_audit_job_fate` swallows
  disk/attribution/serialization failure so it can abort neither request handling nor
  daemon startup; a fate record's attribution reads only `project_path` (canonicalised
  to `project_root`) and `plan_id` from the stored spec — never `command` or any other
  secret-bearing field.

## Bug found and fixed in-run

`Daemon._admit_ready` could re-execute an **already-terminalized** job: it would re-run
the build, clobber the terminal journal status back to `running`, and append a SECOND
`job_fate` record for a single terminalization. Root-caused in TASK-007 from a duplicate
`job_fate` test failure and fixed with an `_is_terminalized` guard that releases the
admission (freeing slot + idempotency fingerprint) instead of running it. Absence of a
journal entry deliberately reads as NOT terminalized — absence is not evidence of an
outcome.

## Residue the epic should track

- **A spec premise was wrong and survived to execute.** D4(b) asserted that a daemon
  restart mid-flight yields an undeterminable fate. It does not: `replay_on_restart`
  forces such a job to `killed`, which IS its real terminal fate. The deliverable was
  re-grounded during execution and the genuinely-unknowable set corrected to
  (GC'd journal entry, daemon that never came back). Emitted separately as a
  candidate-lesson.
- **PLAN-59 boundary held.** The standing `exit_code: 0` timed-out-build-recording
  defect was not absorbed here; nothing in the daemon's timeout path was found to
  share the mechanism at this plan's depth.
- **Two verified cross-cutting defects surfaced** (both emitted separately as
  candidate-lessons, both this epic's own archetype — a confident signal that hides or
  misnames its caveat): `check_auth_cli` collapsing a missing binary into
  "Not authenticated", and `quality-gate` being a strictly weaker mypy gate than
  `verify` while being the standing pre-commit rule.

## Run signals

- 7 Q-Gate findings raised AND resolved in-run (outline false premise; duplicate
  `job_fate` test failure; 3× mypy `no-any-return` in test helpers; 1 PR comment).
- 1 automated-review comment promoted; 0 actionable after triage.
- 1 script-failure cluster: `automatic-review` returned `provider_unconfigured`
  "Not authenticated" when `gh` was merely absent from PATH.
- CI green, review-retrospective clean.
