---
name: manage-locks
description: Cross-session coordination primitives — the unified file-based merge mutex fronted by a FIFO admission queue for fair merge ordering, and the build-queue concurrency limiter, on one shared, TOCTOU-safe read-modify-write + plan-liveness core
user-invocable: false
mode: script-executor
scope: global
---

# Manage Locks Skill

The single home for cross-session coordination primitives in plan-marshall. Both
primitives serialize concurrent sessions regardless of which worktree the caller
is pinned to, and both sit on one shared, TOCTOU-safe read-modify-write +
plan-liveness core (`scripts/_locks_core.py`). They differ in scope: the merge
mutex is **per-repo main-anchored** (it serializes one repository's merges to its
own `main`), while the build-queue limiter is **machine-global** (it caps build
concurrency across every checkout on the host, so its state lives under the
machine-global home root, not the per-repo main checkout). The skill is
`script-deterministic` — pure file coordination, no LLM judgement.

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
  crashed holder's lock AND prunes a crashed waiter's FIFO entry — but a
  live-worktree guard refuses the automatic reclaim on a mid-recovery holder
  (plan-dir-dead but its worktree directory still present), returning a
  `stale_holder_live_worktree` blocked signal for operator confirmation instead of
  force-releasing it; a `blocked` + `blocking_plan_id` admission payload (distinct
  from a hard error) drives the Pre-Merge Gate's poll loop and last-resort
  orchestrator escalation.
- **The build-queue limiter** (`scripts/build_queue.py`, notation
  `plan-marshall:manage-locks:build_queue`) — a bounded-`k`-slot admitter with a
  FIFO waiting queue, persisted in the machine-global `build-queue.json` under the
  home root (`~/.plan-marshall/build-queue.json`, overridable via
  `PLAN_MARSHALL_HOME`). It caps how many build sessions run concurrently across
  every checkout on the host; each entry is stamped with its originating
  checkout's `project_root` so a foreign project's live holder is judged against
  its own repo and never reclaimed.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run scripts via the executor; parse TOON output for `status` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the lock file (`merge.lock`) or the queue file (`build-queue.json`) directly — every mutation goes through the script API so the atomic `O_EXCL` / serialized read-modify-write invariant holds.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not re-implement holder-liveness or main-anchored read-modify-write in a consumer — import the shared helpers from `_locks_core` so there is one TOCTOU-safe serialization surface, not parallel copies.
- Do not add a second main-anchored resolution path for per-repo state — route `merge.lock` and `merge-queue.json` through `resolve_main_anchored_path` (the single ADR-002 sanctioned utility). Route `build-queue.json` through `home_root()` (the machine-global tier), NOT `resolve_main_anchored_path` — the build queue is host-wide, and binding it to one repository's main checkout would break cross-repo build coordination.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format` for the full specification).
- Entry-point scripts (`merge_lock.py`, `build_queue.py`) are invoked only through `python3 .plan/execute-script.py` with the 3-part notation; `_locks_core.py` is an importable module (underscore-prefixed), consumed by the entry-point scripts via PYTHONPATH, never invoked directly.

## Storage Location

The merge-mutex files live under the MAIN checkout's `.plan/local`, resolved via
the single sanctioned `resolve_main_anchored_path` utility (ADR-002), so every
session in one repository contends for the same file regardless of its pinned
cwd. The build-queue file is machine-global — it lives under the home root
(`home_root()`) so every checkout on the host shares one slot budget:

```text
<main>/.plan/local/merge.lock          # the unified merge mutex (one-line holder plan_id)
<main>/.plan/local/merge-queue.json    # the merge-lock FIFO admission queue (waiting state)
~/.plan-marshall/build-queue.json      # the machine-global build-queue active + waiting + run-log state
```

## Anchoring: per-repo main vs machine-global home root

Every other path resolution in the codebase is uniform cwd-relative (see
`tools-script-executor/standards/cwd-policy.md` and `file_ops.get_base_dir`). The
coordination files are the deliberate exceptions, but they split across two tiers:

- **Per-repo main-anchored (ADR-002)** — the merge mutex (`merge.lock`,
  `merge-queue.json`) serializes ONE repository's merges to its own `main`, so it
  routes through the single sanctioned
  `marketplace_paths.resolve_main_anchored_path` utility — the ONE mechanism
  covering the per-repo bounded exception set (`merge.lock`, `merge-queue.json`,
  `run-configuration.json`, `lessons-learned`, `orchestrator`). New **per-repo**
  cross-session shared state MUST route through that utility rather than
  re-implementing git-common-dir resolution.
- **Machine-global home root (ADR-008)** — the build queue coordinates build
  concurrency across EVERY checkout on the host, so `build-queue.json` lives under
  `marketplace_paths.home_root()` (`~/.plan-marshall`, overridable via
  `PLAN_MARSHALL_HOME`), NOT the per-repo main-anchored utility. Machine-wide state
  belongs here, not in the per-repo exception set above.

See ADR-002 (`doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc`)
and ADR-008 (`doc/adr/008-machine-global-home-root-anchor-tier.adoc`).

## Shared Core (`scripts/_locks_core.py`)

The shared core is the TOCTOU / check-then-act mitigation surface for every
consumer. It exposes:

- `holder_is_dead(holder, project_root=None)` — the plan-liveness predicate. A
  holder is dead when its plan directory exists in NEITHER
  `{root}/.plan/local/plans/{holder}` NOR
  `{root}/.plan/local/worktrees/{holder}/.plan/local/plans/{holder}`, where
  `{root}` is the supplied `project_root` when given, else the CALLING project's
  main checkout (cwd-independent). The optional `project_root` parameter
  project-qualifies the liveness check for machine-global consumers: under the
  machine-global build queue (ADR-008) a session in project B checking a holder
  recorded by project A must resolve liveness against A's checkout — the queue
  stamps each entry with its acquirer's `project_root` and the prune forwards it,
  so a foreign project's LIVE holder is never falsely reclaimed. The merge-lock
  caller passes nothing and keeps the caller-anchored behaviour unchanged. An
  empty/malformed holder is treated as dead (a corrupt lock is reclaimable);
  resolution failures propagate loudly. Checking both paths is load-bearing — an
  actively-executing holder's plan dir has been MOVED into the worktree
  (ADR-002), so a main-only check would wrongly declare it dead and let a
  concurrent acquirer steal the lock. Its FIFO-prune contract (dropping a
  crashed waiter's queue entry) is unchanged.
- `holder_has_live_worktree(holder)` — a STRONGER presence/heartbeat liveness
  signal that gates automatic stale-reclaim. It returns True when the holder's
  git worktree directory `<main>/.plan/local/worktrees/{holder}` is still present
  (the directory ITSELF, not the plan dir that lives inside it — the check
  `holder_is_dead` consults). A holder judged dead-by-plan-dir-absence may still
  be MID-RECOVERY — its worktree is on disk but the plan dir has been moved out
  (an interrupted finalize move-back). The `merge_lock` acquire path evaluates
  this guard BEFORE the auto-reclaim branch and REFUSES to reclaim a
  plan-dir-dead-but-live-worktree holder (see the `stale_holder_live_worktree`
  blocked payload below); the FIFO prune retains such a waiter rather than
  dropping it. Anchored at main (cwd-independent) exactly like `holder_is_dead`;
  an empty/malformed holder → False.
- `rmw_json(path, mutate)` — the TOCTOU-safe read-modify-write helper for JSON
  state files. It is path-agnostic: the CALLER resolves the path (main-anchored
  for the merge queue, machine-global under `home_root()` for the build queue). It
  serializes the mutation (an `O_EXCL` guard / atomic temp-file replace) so two
  sessions cannot both observe the same pre-state and both claim a slot/lock. A
  missing or corrupt file is treated as empty (`{}`). It is the single
  read-modify-write mechanism BOTH the build queue (`build-queue.json`) and the
  merge lock's FIFO admission queue (`merge-queue.json`) build on; the merge lock's final `k=1` grant stays the
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
  - **`stale_holder_live_worktree: true`** — a distinct blocked sub-case (present
    ONLY on this path; the ordinary non-front / foreign-live-holder blocked payload
    omits the field). It is the refuse-auto-reclaim signal a
    plan-dir-dead-but-live-worktree holder produces: acquire found the holder dead
    by plan-dir absence but its worktree directory is still on disk
    (`holder_has_live_worktree` True), so it REFUSES to force-release a possibly
    mid-recovery holder and returns this discriminator instead. The existing
    branch-cleanup budget-exhaustion escalation surfaces it to the operator for
    explicit confirmation. No new force-release CLI verb exists — the acquire
    surface is unchanged apart from this added discriminator.

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
