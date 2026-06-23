---
name: manage-locks
description: Cross-session coordination primitives — the unified file-based merge mutex fronted by a FIFO admission queue for fair merge ordering, and the build-queue concurrency limiter, on one shared, TOCTOU-safe, main-anchored core
user-invocable: false
mode: script-executor
scope: global
---

# Manage Locks Skill

The single home for cross-session coordination primitives in plan-marshall. Both
primitives serialize concurrent sessions against the MAIN checkout regardless of
which worktree the caller is pinned to, and both sit on one shared,
TOCTOU-safe, main-anchored read-modify-write + plan-liveness core
(`scripts/_locks_core.py`). The skill is `script-deterministic` — pure file
coordination, no LLM judgement.

Two primitives live here:

- **The unified merge mutex** (`scripts/merge_lock.py`, notation
  `plan-marshall:manage-locks:merge_lock`) — a file-based `O_EXCL` mutex fronted by
  a FIFO admission queue that serializes merge-to-main across
  concurrently-finalizing plans with fair ordering. It is the single merge
  serializer used by BOTH `integrate_into_main`'s inner move-back mutex and the
  `branch-cleanup.md` Pre-Merge Gate. `acquire` FIFO-enqueues the plan into the
  main-anchored `merge-queue.json` (idempotently, preserving FIFO position on
  re-poll, managed through the same `_locks_core.rmw_json` the build queue uses),
  admits ONLY the FIFO-front plan, and on a successful `O_EXCL` create returns
  `admission: admitted`; a non-front or lock-contended plan returns
  `admission: blocked` — a structured re-poll signal, NOT an internal wait (the
  consumer's poll/backoff loop owns the wait). `O_EXCL` atomicity guarantees
  exactly one holder; plan-liveness reclamation (across main + worktree) frees a
  crashed holder's lock AND prunes a crashed waiter's FIFO entry; a `blocked` +
  `blocking_plan_id` admission payload (distinct from a hard error) drives the
  Pre-Merge Gate's poll loop and last-resort orchestrator escalation.
- **The build-queue limiter** (`scripts/build_queue.py`, notation
  `plan-marshall:manage-locks:build_queue`) — a bounded-`k`-slot admitter with a
  FIFO waiting queue, persisted in the main-anchored `build-queue.json`. It caps
  how many build sessions run concurrently across the cluster.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run scripts via the executor; parse TOON output for `status` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the lock file (`merge.lock`) or the queue file (`build-queue.json`) directly — every mutation goes through the script API so the atomic `O_EXCL` / serialized read-modify-write invariant holds.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not re-implement holder-liveness or main-anchored read-modify-write in a consumer — import the shared helpers from `_locks_core` so there is one TOCTOU-safe serialization surface, not parallel copies.
- Do not add a second main-anchored resolution path — route `build-queue.json` and `merge.lock` through `resolve_main_anchored_path` (the single ADR-002 sanctioned utility).

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format` for the full specification).
- Entry-point scripts (`merge_lock.py`, `build_queue.py`) are invoked only through `python3 .plan/execute-script.py` with the 3-part notation; `_locks_core.py` is an importable module (underscore-prefixed), consumed by the entry-point scripts via PYTHONPATH, never invoked directly.

## Storage Location

Both coordination files live under the MAIN checkout's `.plan/local`, resolved via
the single sanctioned `resolve_main_anchored_path` utility (ADR-002), so every
session contends for the same file regardless of its pinned cwd:

```
<main>/.plan/local/merge.lock          # the unified merge mutex (one-line holder plan_id)
<main>/.plan/local/merge-queue.json    # the merge-lock FIFO admission queue (waiting state)
<main>/.plan/local/build-queue.json    # the build-queue active + waiting + run-log state
```

## Main-Anchored Resolution (ADR-002 Bounded Exception)

Every other path resolution in the codebase is uniform cwd-relative (see
`tools-script-executor/standards/cwd-policy.md` and `file_ops.get_base_dir`). The
merge lock and the build queue are deliberate exceptions: cross-session
coordination is inherently main-scoped, so phase-5+ callers pinned to their own
worktrees must all contend for one shared file on main. Both route through the
single sanctioned `marketplace_paths.resolve_main_anchored_path` utility — the ONE
mechanism covering the bounded exception set (`merge.lock`, `merge-queue.json`,
`run-configuration.json`, `lessons-learned`, `build-queue.json`). New
cross-session shared state MUST route through that utility rather than
re-implementing git-common-dir resolution. See
ADR-002 (`doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc`).

## Shared Core (`scripts/_locks_core.py`)

The shared core is the TOCTOU / check-then-act mitigation surface for every
consumer. It exposes:

- `holder_is_dead(holder)` — the plan-liveness predicate. A holder is dead when
  its plan directory exists in NEITHER `<main>/.plan/local/plans/{holder}` NOR
  `<main>/.plan/local/worktrees/{holder}/.plan/local/plans/{holder}` (both anchored
  at main, cwd-independent). An empty/malformed holder is treated as dead (a
  corrupt lock is reclaimable); resolution failures propagate loudly. Checking
  both paths is load-bearing — an actively-executing holder's plan dir has been
  MOVED into the worktree (ADR-002), so a main-only check would wrongly declare it
  dead and let a concurrent acquirer steal the lock.
- `rmw_json(path, mutate)` — the TOCTOU-safe main-anchored read-modify-write
  helper for JSON state files. It serializes the mutation (an `O_EXCL` guard /
  atomic temp-file replace) so two sessions cannot both observe the same
  pre-state and both claim a slot/lock. A missing or corrupt file is treated as
  empty (`{}`). It is the single read-modify-write mechanism BOTH the build queue
  (`build-queue.json`) and the merge lock's FIFO admission queue
  (`merge-queue.json`) build on; the merge lock's final `k=1` grant stays the
  atomic `O_EXCL` create on `merge.lock` (NOT `rmw_json`), with `rmw_json` serving
  only the FIFO enqueue/dequeue in FRONT of that grant. The TOCTOU / check-then-act
  mitigation menu lives in `ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards`
  and is not duplicated here.
- `log_lock_event(lock, event, lock_id, **fields)` — the single best-effort
  `[LOCK]` emission point both lock primitives call at each lifecycle point
  (`merge_lock`: acquired / reclaimed / blocked / released; `build_queue`:
  acquired / blocked / released / reaped-stale). It appends a `[LOCK]`-tagged
  line to the single main-anchored global lock-event log (`lock-{date}.log`
  under `.plan/logs/`) — never the per-worktree work-log — because locks are
  cross-session, main-anchored coordination whose event timeline must be shared
  across all sessions. Uses `WARNING` level for `reaped-stale`; `INFO` for
  every other event. The entire body is best-effort: any failure (resolution,
  unwritable dir, encoding) is swallowed so a logging error can never affect
  lock correctness.

Consumers import the core via PYTHONPATH (mirroring how `script-shared` modules
are consumed):

```python
from _locks_core import holder_is_dead, rmw_json, log_lock_event
```

## Canonical invocations

The canonical argparse surface for the two entry-point scripts this skill
registers: `merge_lock.py` and `build_queue.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### merge_lock — acquire

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock acquire \
  --plan-id PLAN_ID [--timeout TIMEOUT] [--no-title-token]
```

`acquire` FIFO-enqueues `--plan-id` into `merge-queue.json` (idempotently — a
re-poll preserves the plan's FIFO position), admits ONLY the FIFO-front plan, and
is **non-blocking for the queue case** — re-polling is the consumer's job (the
Pre-Merge Gate's poll/backoff loop). The `--timeout` flag is retained for
call-site compatibility but no longer drives an internal wait. Output carries an
`admission` discriminator:

- **`status: success`, `admission: admitted`** — this plan is the FIFO front and
  holds the `O_EXCL` lock (`action: acquired`, or `action: already_held` on a
  reentrant self-holder re-acquire). Fields: `holder`, `lock_path`, `reclaimed`,
  `waiting_count`.
- **`status: blocked`, `admission: blocked`** — this plan is NOT the FIFO front,
  or is the front but a FOREIGN live holder holds the lock. A structured re-poll
  signal (NOT a hard error). Fields: `blocking_plan_id`, `lock_path`,
  `waiting_count`. The consumer re-polls (preserving FIFO position) until
  `admission: admitted` or its wait budget is exhausted, then fires the last-resort
  `AskUserQuestion`.

### merge_lock — check

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock check \
  --plan-id PLAN_ID
```

### merge_lock — release

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id PLAN_ID [--no-title-token]
```

### build_queue — acquire

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue acquire \
  --plan-id PLAN_ID
```

### build_queue — release

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue release \
  --plan-id PLAN_ID --id ID
```

## Integration

| Producer / Consumer | Direction | Notation |
|---------------------|-----------|----------|
| `workflow-integration-git:integrate_into_main` | consumes | `merge_lock acquire`/`release` around the move-back |
| `phase-6-finalize/standards/branch-cleanup.md` Pre-Merge Gate | consumes | `merge_lock acquire` (FIFO poll/backoff loop on `admission: blocked`)/`check`/`release` |
| build wrappers (`_build_execute_factory`, `_pyproject_execute`) | consume | `build_queue acquire`/`release` around `execute_direct` (D6) |
| `_locks_core.rmw_json` | consumed by | both `build_queue` (`build-queue.json`) and `merge_lock` (`merge-queue.json` FIFO layer) |

## Related

- `plan-marshall:script-shared` — provides `marketplace_paths.resolve_main_anchored_path` (the main-anchored resolver) and `triage_helpers` (CLI/error helpers).
- `plan-marshall:workflow-integration-git` — `integrate_into_main` consumer of the merge mutex.
- `plan-marshall:ref-code-quality` — the TOCTOU / check-then-act mitigation menu the shared core implements.
