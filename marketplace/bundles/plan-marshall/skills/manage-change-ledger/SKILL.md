---
name: manage-change-ledger
description: The single append-only change-ledger — one worktree_sha-stamped substrate for kind=build, kind=change, and kind=job entries — plus the first-class worktree-sha freshness API
user-invocable: false
mode: script-executor
scope: global
---

# Manage Change-Ledger Skill

The single home for the unified, append-only **change-ledger** in plan-marshall
and the **first-class `worktree_sha` freshness API** over it. The skill is
`script-deterministic` — pure record-keeping and a git-native currency hash, no
LLM judgement. It is modeled on `manage-locks`: a tracked-config-dir primitive
that is NOT plan-scoped, so it serves plan-less orchestrator builds as well as
plan-scoped task builds.

There is exactly ONE ledger file, ONE `worktree_sha` primitive (a single shared
implementation), and ONE append verb. Entries are **pure-append** — no
find-and-update, no in-place mutation. There is no separate registry file anywhere.

## The `worktree_sha` primitive — working-tree currency, not HEAD currency

`compute_worktree_sha(worktree_root)` lives ONCE in
`script-shared/scripts/worktree_sha.py` and is the **sole** implementation
imported by the `worktree-sha` verb, the executor `kind=build` writer, and the
`pre-commit-verify-freshness` gate. The writer/gate symmetry is
correctness-critical — a divergent hash silently breaks every freshness match —
so the helper is imported, never re-implemented.

The primitive is the **working-tree** currency hash: the committed base
(`git rev-parse HEAD`) + the full tracked diff against it (`git diff HEAD`,
staged AND unstaged) + the sorted content of untracked-not-ignored files
(`git ls-files --others --exclude-standard`), hashed with `sha256`. It captures
the **uncommitted** plan edits, NOT the committed HEAD sha. This is mandatory
because the freshness gate is a *pre-commit* gate: a `git rev-parse HEAD`
primitive would match trivially (the pre-plan commit sha is the same at build
time and at gate time regardless of working-tree changes), producing a
false-positive `fresh`. On a clean tree the digest reduces to a stable function
of HEAD alone (the clean-tree HEAD-tree fallback). The helper NEVER mutates the
working tree, index, or refs (no `git stash`, no `git write-tree`, no `git add`).

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run scripts via the executor; parse TOON output for `status` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the ledger file (`change-ledger.jsonl`) directly — every write goes through the `append` verb / the `append_entry` core so the pure-append, one-line-per-record invariant holds.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not re-implement the `worktree_sha` hash or the JSONL read in a consumer — import `compute_worktree_sha` from `worktree_sha` and `read_entries`/`resolve_ledger_path` from `_ledger_core`, so there is one byte-identical implementation, not parallel copies.
- Do not self-compute or snapshot a `kind=change` entry's `changed_paths` from a deliverable's declared `affected_files` — the paths MUST be git-sourced by the caller (`git diff-tree --no-commit-id --name-only -r {commit_sha}`); the verb stores the supplied list verbatim.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format` for the full specification).
- The entry-point script (`manage-change-ledger.py`) is invoked only through `python3 .plan/execute-script.py` with the 3-part notation; `_ledger_core.py` is an importable module (underscore-prefixed), consumed via PYTHONPATH, never invoked directly. `compute_worktree_sha` lives in `script-shared` and is imported, not duplicated.

## Storage Location

One ledger file, resolved via `get_tracked_config_dir()` (NOT plan-scoped), so
every writer (including a plan-less orchestrator build) appends to the same file:

```text
<tracked-config-dir>/work/change-ledger.jsonl
```

## Entry Shapes

Every entry carries a `kind` discriminator, a `worktree_sha`, and a
`timestamp_iso` (UTC ISO-8601). Three kinds:

- **`kind=build`** — written by the executor dispatch boundary after every
  build-class invocation that runs to completion. Fields: `kind: "build"`,
  `notation`, `plan_id` (str|null — null for an orchestrator global-tier
  build), `args`, `exit_code` (int, recorded even when non-zero — orthogonal
  diagnostic detail), `status` (the truthful build outcome of record —
  `success` | `error` | `timeout` | `killed` — derived at the boundary from
  the returncode and the wrapper's stdout TOON; a timed-out build stamps
  `status: timeout` despite its exit code 0, and a child killed by a POSIX
  signal stamps `status: killed`), `worktree_sha`, `log_file`,
  `timestamp_iso`. A build is NOT a commit, so a `kind=build` entry does NOT
  carry `commit_sha` or `changed_paths`. The stamp is **tier-agnostic** —
  written at the executor dispatch boundary, it fires identically for an
  inline `per_task` build and for an `orchestrator`-tier build detached via
  the `await-long-running` seam — but ONLY for jobs whose executor process
  survives to the boundary. A job whose whole process tree is killed dies
  BEFORE the boundary runs and stamps nothing at all: **a missing row is
  itself a signal** (no row + zero output bytes is the whole-tree-kill
  signature). The freshness gate matches on `worktree_sha` + `status ==
  success` alone and never inspects the tier, the background flag, or the
  exit code.
- **`kind=change`** — written by the phase-5 execute loop after each deliverable
  completes-and-commits. Fields: `kind: "change"`, `deliverable_id` (or
  `task_id`), `commit_sha`, `changed_paths` (the **git-sourced** list, stored
  verbatim), `worktree_sha` (post-commit), `timestamp_iso`.
- **`kind=job`** — written by the `build-server-client` skill's `submit` verb at
  submit time. Fields: `kind: "job"`, `job_id` (the daemon-assigned id),
  `plan_id` (str|null), `fingerprint` (the idempotent-submit digest the daemon
  scheduler keys on), `notation` (the executor notation dispatched),
  `worktree_sha`, `timestamp_iso`. Unlike `kind=build` (a completed build
  outcome) this is a **submission** record — the job may still be running — so it
  carries no `exit_code` or `status`. Its purpose is **re-attach**: a rebuilt or
  harness-reaped session reads the most recent `kind=job` row for its plan and
  re-issues `wait` against the recorded `job_id`, recovering the in-flight build
  from plan state alone rather than losing it.

The freshness gate consumes only `kind=build` entries; `kind=change` and
`kind=job` entries make the ledger a complete, reusable record of working-tree
transitions and in-flight build submissions.

## Canonical invocations

The canonical argparse surface for the entry-point script this skill registers:
`manage-change-ledger.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### manage-change-ledger — worktree-sha

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger worktree-sha \
  [--worktree-root WORKTREE_ROOT]
```

### manage-change-ledger — append (kind=build)

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger append \
  --kind build --notation NOTATION --exit-code EXIT_CODE --status {success|error|timeout|killed} \
  [--plan-id PLAN_ID] [--args ARGS] [--log-file LOG_FILE] \
  [--worktree-root WORKTREE_ROOT] [--worktree-sha WORKTREE_SHA]
```

### manage-change-ledger — append (kind=change)

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger append \
  --kind change --deliverable-id DELIVERABLE_ID --commit-sha COMMIT_SHA --changed-paths CHANGED_PATHS \
  [--task-id TASK_ID] [--worktree-root WORKTREE_ROOT] [--worktree-sha WORKTREE_SHA]
```

### manage-change-ledger — append (kind=job)

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger append \
  --kind job --job-id JOB_ID \
  [--plan-id PLAN_ID] [--fingerprint FINGERPRINT] [--notation NOTATION] \
  [--worktree-root WORKTREE_ROOT] [--worktree-sha WORKTREE_SHA]
```

Persists a daemon-assigned `job_id` at submit time so a rebuilt session can
re-attach to the in-flight build. Written by the `build-server-client` skill's
`submit` verb (which imports `job_record` + `append_entry` from `_ledger_core`
directly); this verb is the equivalent executor surface for tests and manual use.

### manage-change-ledger — query

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger query \
  [--kind build|change|job] [--exit-code EXIT_CODE]
```

### manage-change-ledger — classify-outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger classify-outcome \
  --job-status {completed|killed} --output-bytes OUTPUT_BYTES \
  --worktree-sha WORKTREE_SHA
```

The deterministic killed-job classifier — a pure function of three observable
inputs (the harness-reported job status, the byte count of the job's captured
output, and the presence of a matching `kind=build` ledger row, most-recent
first and scoped to the required `--worktree-sha`) returning a fixed
`verdict`. `--worktree-sha` is required: an unscoped cross-check can match a
stale row stamped against a different worktree state and misclassify a killed
job as `success`. Every call site already holds the sha at call time (the
`await-long-running` seam computes it before dispatch).

- `externally_killed` — the job reported `killed`, OR no matching ledger row
  exists AND `--output-bytes 0`, OR the matching row itself carries
  `status: killed`. The no-row case is the **whole-tree-kill signature**:
  the executor died before the dispatch boundary could stamp a row, so the
  missing row plus the 0-byte output IS the kill evidence. The killed-row
  case is the **child-kill signature**: the executor survived to the
  boundary and stamped the `killed` outcome it observed. The returned TOON's
  `display_detail`/`message` render "externally killed — not flaky, do not
  blind-retry" — the call site MUST NOT re-dispatch the identical command as
  a retry.
- `timeout` — a matching row carries `status: timeout` (a clean timeout is
  never classified as a kill).
- `success` — a matching row carries `status: success`.
- `undecidable` — anything else.

The classifier reads the ledger through `_ledger_core.read_entries` — never a
re-implemented JSONL read.

## Shared Core (`scripts/_ledger_core.py`)

The deterministic core exposes the single read/write/construct surface every
consumer imports via PYTHONPATH:

```python
from _ledger_core import (
    resolve_ledger_path, append_entry, read_entries,
    build_record, change_record, job_record,
)
```

- `resolve_ledger_path()` — `get_tracked_config_dir() / 'work' / 'change-ledger.jsonl'` (NOT plan-scoped).
- `append_entry(record)` — append exactly one `json.dumps(record) + '\n'` line. Pure-append; no read-modify-write.
- `read_entries()` — parse the JSONL line-by-line, skip malformed lines, return `[]` when absent. The library reader the gate imports directly.
- `build_record(...)` / `change_record(...)` / `job_record(...)` — constructors that stamp `kind`, `worktree_sha`, `timestamp_iso` and the kind-specific fields, so every writer and the CLI produce identically-shaped entries. `change_record` stores the caller-supplied `changed_paths` verbatim — it does NOT compute changed paths. `job_record` persists a submit-time `job_id` (+ `fingerprint` / `notation`) for build re-attach.

## Integration

| Producer / Consumer | Direction | Notation |
|---------------------|-----------|----------|
| `tools-script-executor` dispatch boundary | produces | `append --kind build` (executor template `kind=build` writer) |
| `phase-5-execute` Step 10a chain-tail | produces | `append --kind change` after each per-deliverable commit |
| `build-server-client` `submit` verb | produces | imports `job_record` + `append_entry`; writes `kind=job` at submit time for re-attach |
| `build-server-client` `wait` re-attach | consumes | imports `read_entries`; reads the latest `kind=job` for the plan to recover `job_id` |
| `manage-tasks:pre-commit-verify-freshness` gate | consumes | imports `read_entries` + `compute_worktree_sha`; scans `kind=build` by `status == success` + `worktree_sha` |

## Related

- `plan-marshall:script-shared` — home of `worktree_sha.compute_worktree_sha` (the single shared freshness primitive) and `triage_helpers` (CLI/error helpers).
- `plan-marshall:manage-locks` — the sibling tracked-config-dir coordination primitive this skill's shape is modeled on.
- `plan-marshall:manage-tasks` — owner of the `pre-commit-verify-freshness` gate that consumes the ledger.
- `plan-marshall:ref-code-quality` — the TOCTOU / check-then-act mitigation menu the pure-append shape deliberately avoids.
