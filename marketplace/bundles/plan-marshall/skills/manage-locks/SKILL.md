---
name: manage-locks
description: Cross-session coordination primitives — the unified file-based merge mutex fronted by a FIFO admission queue for fair merge ordering, the cross-plan review-bot rate-window claim co-tenanting that store, and the build-queue concurrency limiter, on one shared, TOCTOU-safe read-modify-write + plan-liveness core
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
  (plan-dir-dead but its worktree still genuinely live — a git-worktree marker or
  live plan dir present, not a bare orphaned shell), returning a
  `stale_holder_live_worktree` blocked signal for operator confirmation instead of
  force-releasing it; a `blocked` + `blocking_plan_id` admission payload (distinct
  from a hard error) drives the Pre-Merge Gate's poll loop and last-resort
  orchestrator escalation. The same entry point also carries the **rate-window
  claim** (`rate-window claim` / `check` / `release`) — a cross-plan claim on ONE
  review bot's rate window that shares the merge-lock STORE but never the merge
  MUTEX (see below) — and the **`poll-delay`** computation, a bounded jittered
  delay for a caller about to wake from an elapsed rate window. `poll-delay` shares
  neither the store nor the mutex: it is a pure computation that touches no state
  and never sleeps, returning the number for its CALLER to wait.
- **The build-queue limiter** (`scripts/build_queue.py`, notation
  `plan-marshall:manage-locks:build_queue`) — a bounded-`k`-slot admitter with a
  FIFO waiting queue, persisted in the machine-global `build-queue.json` under the
  home root (`~/.plan-marshall/build-queue.json`, overridable via
  `PLAN_MARSHALL_HOME`). It caps how many build sessions run concurrently across
  every checkout on the host; each entry is stamped with its originating
  checkout's `project_root` so a foreign project's live holder is judged against
  its own repo and never reclaimed. It is the **single shared reader/writer of the
  one machine-global slot file**, consumed by BOTH build-execute paths:
  marshalld's scheduler on the registered path (the daemon coordinates access to
  the same file for builds it serves) AND the in-process fallback
  (`_build_queue_slot`) on the unregistered / daemon-down path. There is no
  separate project-level queue — one file, one slot budget, one path per build,
  never stacked; a build routed to the daemon takes no fallback slot. The
  byte-identical-unregistered guarantee holds through this shared file: an
  unregistered build still touches no daemon or socket, yet acquires its slot
  against the same global file exactly as before. It exposes **four** actions —
  two slot actions (`acquire` / `release`) and two threshold actions (`limit get`
  / `limit set`). Both of the values it admits against are machine-global too: the
  slot cap `max_slots` resolves from `machine-config.json` through the shared
  cwd-independent resolver (NOT the calling repository's `marshal.json`), and the
  adaptive stale-reclaim threshold `upper_limit_seconds` is a top-level field of
  `build-queue.json` itself — see **The cap and the reap threshold are
  machine-global** below.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run scripts via the executor; parse TOON output for `status` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the lock file (`merge.lock`) or either state file (`merge-queue.json`, `build-queue.json`) directly — every mutation goes through the script API so the atomic `O_EXCL` / serialized read-modify-write invariant holds.
- Do not couple the rate-window claim to the merge mutex — a `rate-window` action must never acquire, contend for, or release `merge.lock`, and must never read or mutate the `waiting` FIFO list. The two claims share the store, not the mutex.
- Do not return a freshly-constructed state dict from an `rmw_json` mutator — merge into the state handed in, so a co-tenant top-level key is never silently erased.
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
<main>/.plan/local/merge-queue.json    # the merge-lock store: `waiting` (FIFO admission) + `rate_windows` (per-bot claims)
~/.plan-marshall/build-queue.json      # the machine-global build-queue active + waiting + run-log state, plus the top-level `upper_limit_seconds` reap threshold
~/.plan-marshall/marshalld/machine-config.json  # the machine-global build-slot cap `max_slots` (read here, written only by manage-build-server `config set` / `config migrate`)
```

## The rate window shares the STORE, never the MUTEX

`merge-queue.json` is a **shared store with two independent top-level keys**, not a
single queue file:

- `waiting` — the FIFO admission queue in FRONT of the `k=1` `merge.lock` mutex.
  Owned exclusively by `acquire` / `release`.
- `rate_windows` — the per-`bot_kind` rate-window claims. Owned exclusively by the
  `rate-window` verbs.

Claiming a bot's rate window **does not serialize against merges**. No `rate-window`
action creates, reads, reclaims, or releases `merge.lock`, and none reads or mutates
the `waiting` list; conversely no merge action reads or mutates `rate_windows`.
Coupling a review bot's multi-minute cooldown to the merge serializer would stall
every concurrently-finalizing plan's merge behind that cooldown. The two claims
share nothing but the brief `_locks_core.rmw_json` guard both mutations serialize
on — which is exactly why the FIFO mutators **merge** their result into the state
they were handed rather than returning a freshly-constructed `{"waiting": ...}`: a
wholesale replace would silently erase the co-tenant `rate_windows` key on the next
merge acquire.

## Anchoring: per-repo main vs machine-global home root

Every other path resolution in the codebase is uniform cwd-relative (see
`tools-script-executor/standards/cwd-policy.md` and `file_ops.get_base_dir`). The
coordination files are the deliberate exceptions, but they split across two tiers:

- **Per-repo main-anchored (ADR-002)** — the merge mutex (`merge.lock`,
  `merge-queue.json`) serializes ONE repository's merges to its own `main`, so it
  routes through the single sanctioned
  `marketplace_paths.resolve_main_anchored_path` utility — the ONE mechanism
  covering the per-repo bounded exception set (`merge.lock`, `merge-queue.json`,
  `run-configuration.json`, `lessons-learned`, `orchestrator`,
  `plans/NO_PLAN/build-results`). New **per-repo**
  cross-session shared state MUST route through that utility rather than
  re-implementing git-common-dir resolution.
- **Machine-global home root (ADR-008)** — the build queue coordinates build
  concurrency across EVERY checkout on the host, so `build-queue.json` lives under
  `marketplace_paths.home_root()` (`~/.plan-marshall`, overridable via
  `PLAN_MARSHALL_HOME`), NOT the per-repo main-anchored utility. Machine-wide state
  belongs here, not in the per-repo exception set above.

See ADR-002 (`doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc`)
and ADR-008 (`doc/adr/008-machine-global-home-root-anchor-tier.adoc`).

## The cap and the reap threshold are machine-global

Both values the build queue admits and reaps against are machine-global, for the
same reason the queue file itself is: they are applied to EVERY repository's
entries in the one shared queue, so a per-repo value is one a caller can hold while
contending against a caller holding a different one.

**The cap.** `max_slots` resolves through the shared
`_machine_config.resolve_max_slots()` from `~/.plan-marshall/marshalld/machine-config.json`
— never the calling repository's `marshal.json`. The resolver is cwd-independent, so
a process that has moved its working directory (the daemon's post-`double_fork`
`chdir('/')`) can no longer degrade silently to the default. Every `acquire` /
`release` result therefore reports `max_slots_source` beside `max_slots`. The
source vocabulary and the operator verbs that write the file are documented where
that script is — [`manage-build-server/SKILL.md`](../manage-build-server/SKILL.md)
§ "The machine-global build-slot cap".

**The reap threshold.** `upper_limit_seconds` is a TOP-LEVEL field of
`build-queue.json` — the same file whose entries it governs — rather than a per-repo
key in the main-anchored `run-configuration.json`. Under a per-repo value, a repo
that had never seen a long build could reap another repo's live long build early,
while each repo's releases ratcheted only its own copy; living in the queue's own
state makes it single-valued host-wide by construction. It is read and written
INSIDE the queue's own `rmw_json` critical section on every path: the reaper reads
it from the state it is already mutating, `release` recomputes `max(current, held)`
clamped to `[600, 3600]` there too, and `limit set` writes through the same
mutation. The reaper's threshold is `2 ×` that value. A release persists the
recomputed value ONLY when it actually moves — writing back an unchanged floor would
materialise the field and destroy the `default_floor` / `queue_state` distinction.

**A surviving per-repo value is reported, never honoured.** A `build.queue.max_slots`
in the caller's `marshal.json` is read by `acquire` for the SOLE purpose of reporting
it (`per_repo_max_slots` + a `per_repo_max_slots_not_in_effect` warning); a
`build.queue.upper_limit_seconds` in the caller's `run-configuration.json` is read by
`limit get` for the SOLE purpose of reporting it (`per_repo_value`). Neither value
ever reaches the applied cap or threshold.

### Cap disagreement is reported, never reconciled

Because the cap is resolved per process while the queue is shared host-wide, two
sessions can still admit against different caps — a daemon started before a `config
set`, or a caller whose machine-global file became unreadable. Every new entry is
therefore stamped at admission with **`admitted_under_max_slots`**, the cap it was
actually admitted under. The stamp is written once and never rewritten: a promotion
moves the entry dict from `waiting` to `active` and carries the original stamp with
it.

`acquire` compares its own resolved cap against the stamps of every pre-existing
active and waiting entry and reports `cap_agreement`:

| Verdict | When |
|---------|------|
| `disagree` | At least one stamped entry was admitted under a different cap |
| `unknown` | Nothing disagreed, but at least one entry carries no usable stamp |
| `agree` | Every entry carries a stamp equal to this caller's cap |

`disagree` outranks `unknown`, because a proven disagreement is not made less true
by a second entry that could not be compared. An entry whose stamp is absent, or is
not a positive `int` (a `bool` is rejected despite being an `int` subclass), counts
as unstamped and is **never** counted as agreement — a missing measurement treated
as a match is what would let a real disagreement report as `agree`. See
[scope-limited-negative-is-unknown.md](standards/scope-limited-negative-is-unknown.md).

The verdict always rides with its population (`cap_compared_count` /
`cap_unstamped_count`), so an `agree` can never be read off a comparison that never
happened: publishing the population is what makes an `agree` over an EMPTY queue
visible as such rather than reading like a clean bill of health. The comparison runs
after the reaper and the dead-holder prune — so a reclaimed entry's stamp raises no
conflict nobody can act on — and BEFORE the caller's own entry is appended, so an
empty queue reports `cap_compared_count: 0` rather than counting the entry this very
call is about to create. Both the comparison and the stamp happen inside the SAME
serialized `rmw_json` mutation that admits, so the verdict describes exactly the
queue state the admission decided against.

On a `disagree`, `acquire` emits **one** WARN-level `cap-disagreement` `[LOCK]`
event — one per acquire, not one per disagreeing holder, because the disagreement is
a single property of this admission and the holders ride along as fields
(`caller_max_slots`, `caller_max_slots_source`, `disagreeing_count`,
`compared_count`, `unstamped_count`, `disagreeing_holders`).

**Reporting is the whole of it.** Admission logic is unchanged: the admitting caller
applies ITS OWN cap, existing stamps are left exactly as they were admitted, and
neither value is picked as authoritative. Reconciling the two is deliberately out of
scope, because choosing a winner is what a per-caller cap over a shared queue cannot
do correctly — which is also why the warning names no remedy command.

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
  signal that gates automatic stale-reclaim. It does NOT trust the bare existence
  of the worktree directory `<main>/.plan/local/worktrees/{holder}`: an orphaned
  empty shell (a worktree dir left on disk after a never-persisted plan or an
  incomplete/post-migration finalize teardown, carrying no git plumbing and no
  live plan) would masquerade as mid-recovery under a bare `dir.exists()` check
  and permanently block the merge-lock auto-reclaim. Instead it returns True ONLY
  for a genuine live/mid-recovery worktree — one carrying a concrete live-worktree
  marker under `worktrees/{holder}`: EITHER a git-worktree gitdir link (the `.git`
  marker at the worktree root — a `.git` file pointing at the registered worktree
  admin dir, or a `.git` directory — meaning the git plumbing is still wired up)
  OR a live plan dir moved into the worktree
  (`worktrees/{holder}/.plan/local/plans/{holder}`, present while the plan is
  executing or mid-finalize). It returns False for an orphaned empty shell
  carrying NEITHER marker. A holder judged dead-by-plan-dir-absence may still be
  MID-RECOVERY — its worktree is on disk with git plumbing intact but the plan dir
  has been moved out (an interrupted finalize move-back). The `merge_lock` acquire
  path evaluates this guard BEFORE the auto-reclaim branch and REFUSES to reclaim
  a plan-dir-dead-but-live-worktree holder (see the `stale_holder_live_worktree`
  blocked payload below); the FIFO prune retains such a waiter rather than
  dropping it. Strengthening the predicate only NARROWS the refuse-reclaim set —
  an orphaned shell now permits auto-reclaim while a genuine mid-recovery worktree
  stays protected. Anchored at main (cwd-independent) exactly like
  `holder_is_dead`; an empty/malformed holder → False.
- `holder_staleness(holder, project_root=None)` — the main-anchored three-valued
  staleness verdict (`fresh` / `stale` / `unknown`) that the manual-release recovery
  path consults instead of a cwd-scoped enumeration. It composes the two predicates
  above, consulting ONLY main-anchored paths: `fresh` when the holder is alive or
  mid-recovery (a live worktree present), `stale` only when main-anchored-dead AND
  no live worktree, and `unknown` when the main-anchored `.plan/local` base cannot be
  resolved — surfaced explicitly, NEVER swallowed as `stale` (ADR-009 fail-closed).
  It is the guard against the sibling-worktree misjudgement: a holder live in a
  DIFFERENT worktree reads `fresh` regardless of the querying cwd, so it is never
  force-released. See [scope-limited-negative-is-unknown.md](standards/scope-limited-negative-is-unknown.md).
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
  acquired / blocked / released / reaped-stale / cap-disagreement). It appends a `[LOCK]`-tagged
  line to the single main-anchored global lock-event log (`lock-{date}.log`
  under `.plan/logs/`) — never the per-worktree work-log — because locks are
  cross-session, main-anchored coordination whose event timeline must be shared
  across all sessions. Uses `WARNING` level for `reaped-stale` and
  `cap-disagreement`; `INFO` for
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
registers: `merge_lock.py` and `build_queue.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming docs
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

`--no-title-token` suppresses the terminal-title surface for this call (the
move-back merge lock passes it so no spurious glyph appears). Otherwise `acquire`
writes a ⏳ `lock-waiting` / 🔒 `lock-owned` title token stamped with the
`merge-lock` **owner**; the paired `release` clear is owner-scoped, so a lock
surface can neither clobber a concurrent build bracket's `build-busy` token nor
be clobbered by one. See
[`platform-runtime/standards/terminal-title-architecture.md`](../platform-runtime/standards/terminal-title-architecture.md)
§ Channel Delivery Contract ruling (c) for the record shape and arbitration rule.

### merge_lock — check

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock check \
  --plan-id PLAN_ID
```

A non-mutating holder read: `status: free` when no lock file exists, or
`status: held` + `holder_plan_id` when one does. On the `held` branch it also
surfaces a `staleness` field (`fresh` / `stale` / `unknown`, from
`holder_staleness`) — the authoritative main-anchored verdict the manual-release
recovery recipe consults instead of a cwd-scoped `manage-status list` /
`worktree-list` enumeration.

### merge_lock — release

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id PLAN_ID [--require-stale] [--no-title-token]
```

By default `release` is the unconditional self-holder release (removes the lock
only when this caller is the recorded holder; idempotent no-op otherwise). With
`--require-stale` it becomes a fail-closed recovery release: the removal is
CONDITIONAL on the recorded holder's `holder_staleness` verdict — it evicts only a
provably `stale` holder (through the observed-file eviction arbitration, never a
blind unlink) and REFUSES (`status: refused`, `reason: holder_not_provably_dead`)
on a `fresh` or `unknown` verdict, so a holder live in a sibling worktree is never force-released.

`--no-title-token` matches the acquire-side suppression: the caller never set a
token, so there is nothing to clear. Otherwise the release path issues an
owner-scoped `merge-lock` clear and settles the state for the next render event.

### merge_lock — rate-window claim

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window claim \
  --plan-id PLAN_ID --bot-kind BOT_KIND --pr-number PR_NUMBER \
  [--window-seconds WINDOW_SECONDS] [--attempt-cap ATTEMPT_CAP]
```

Claims `--bot-kind`'s rate window for `--plan-id`, recording the window expiry and
advancing the recovery-attempt counter. `--window-seconds` carries the ETA parsed
from the bot's registry `rate_limit_eta_patterns` (default `3600`). `--attempt-cap`
is the recovery budget per `(bot_kind, pr_number)`; omit it to take the shipped
default, which `rate-window --help` prints — this page names the flag rather than
restating its value, so the number cannot drift out of agreement with the code that
defines it. Idempotent for the self-holder: a re-claim renews the same record in
place rather than contending. `--pr-number` is REQUIRED: the counter is scoped to
the PR, so a claim without one is refused (`status: error`) before the store is
touched. Outcomes:

- **`status: success`** — the claim is held. `action` is `claimed` (first claim),
  `renewed` (self-holder re-claim), or `reclaimed` (the previous holder's window
  elapsed or its plan is dead). Fields: `holder` (this plan), `expires_at`,
  `seconds_remaining`, `attempts`, `attempt_cap`, `attempts_remaining`,
  `reclaimed_from`.
- **`status: blocked`, `reason: window_held_by_other_plan`** — a DIFFERENT live plan
  holds an unexpired window. No mutation. Fields: `holder`, `expires_at`,
  `seconds_remaining`.
- **`status: refused`, `reason: recovery_cap_exhausted`** — the recursion cap
  (`attempt_cap` recovery events per bot per PR) is spent. No mutation; the consumer
  escalates rather than re-triggering the bot. The attempt counter is scoped to
  `(bot_kind, pr_number)` and survives a release, a takeover by another PLAN, and a
  takeover by another PR — the store keeps a per-PR ledger beside the record, so the
  cap can be reset neither by releasing and re-claiming, nor by letting a second PR
  claim the same bot's window in between.

### merge_lock — rate-window check

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window check \
  --plan-id PLAN_ID --bot-kind BOT_KIND --pr-number PR_NUMBER [--attempt-cap ATTEMPT_CAP]
```

A pure non-mutating read: `status: held` while a holder's window is unexpired,
`status: free` otherwise (including a released or elapsed record). Fields: `holder`,
`pr_number`, `expires_at`, `seconds_remaining`, `expired`, `attempts`,
`attempts_for_pr`, `attempt_cap`, `attempts_remaining` — on BOTH branches, including
the one where no record exists yet, so a consumer never branches on whether the
window has been claimed. This is the observable the recovery sequence polls between
paced `sleep` calls — never a single long blocking sleep of the parsed ETA.

`--pr-number` is REQUIRED here for the same reason it is on `claim`: the budget
`check` reports is the budget the caller's PR has left, which is unanswerable
without knowing the PR. A `check` without one is refused (`status: error`) before
the store is read.

Two counts are published because they answer different questions. `attempts` is the
raw stored count for `--bot-kind`, whatever PR it belongs to. `attempts_for_pr` is
the part of it that counts against the CALLER's PR — zero when the stored record
belongs to a different PR, since the cap is scoped to `(bot_kind, pr_number)`.
`attempts_remaining` is derived from `attempts_for_pr`, never from `attempts`.

**Invariant — `check` and `claim` agree.** A `check` immediately followed by a
successful `claim` for the SAME PR reports exactly one more remaining attempt than
that claim does, because both compute the spent count the same way. This is what
makes `check` safe to read before acting: when the two disagreed, a `check` for a
PR the stored record did not belong to reported the budget exhausted while the
`claim` that followed would have succeeded, so a read-before-act consumer skipped a
recovery it was still allowed to run.

### merge_lock — rate-window release

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window release \
  --plan-id PLAN_ID --bot-kind BOT_KIND
```

Drops this plan's claim (`action: released`), or is a benign no-op when the window
is unclaimed or held by another plan (`action: noop`). The record is RETAINED with
its `attempts` counter intact — the recursion cap counts recovery events per bot per
PR across the whole sequence, which releases the window between attempts.

Unlike `claim` and `check`, `release` takes no `--pr-number` and refuses nothing when
it is absent: it drops the holder without consulting the per-PR counter, so it has no
PR to count against.

### merge_lock — poll-delay

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock poll-delay \
  [--min-seconds MIN_SECONDS] [--max-seconds MAX_SECONDS]
```

Returns ONE uniformly-drawn delay in seconds, bounded by `--min-seconds` (default
`300`) and `--max-seconds` (default `1200`) — the 5-to-20-minute range. Output:

- **`status: success`** — fields `delay_seconds` (the drawn value), plus
  `min_seconds` and `max_seconds` echoing the range it was drawn from, so a consumer
  reading only the payload need not know the defaults.
- **`status: error`** (`error_code: INVALID_INPUT`) — the bounds are malformed, in
  exactly three ways, checked in this order. Either bound is **non-finite** (`nan`,
  `inf`, `-inf`): `nan` compares False against every bound so neither check below can
  see it, and both it and `+inf` produce a non-finite draw that reaches the caller's
  `sleep`. Either bound is **negative**: the drawn value is interpolated straight into
  the caller's `sleep` command, so a negative bound leaves this verb as a malformed
  shell command rather than as a merely-odd number. Or `--min-seconds` **exceeds**
  `--max-seconds`: the pair is REFUSED, never silently swapped, because a swap returns
  a plausible delay drawn from a range the caller never asked for, so the caller's
  mistake survives as a wrong-but-believable number instead of surfacing as an error
  it can act on. Every refusal echoes `min_seconds` and `max_seconds`.

**It computes; it does not wait.** The verb returns the number and exits — the
CALLER sleeps it. `automatic-review` awaits it once at the Branch 3 → trigger-arm
boundary of its rate-limit recovery, as a single standalone `sleep` Bash call. The
split is deliberate and matches the rate-window verbs, which are likewise
non-waiting (an atomic claim or release, with the caller re-polling): a wait
embedded in this script would hold a process open inside a primitive every
concurrently-finalizing plan contends on.

**It shares neither the store nor the mutex — it touches no state at all.** Unlike
the `rate-window` verbs, which at least co-tenant `merge-queue.json`, `poll-delay`
is a pure computation behind a CLI. It takes no `--plan-id`, reads no store, and
writes nothing to `merge.lock`, `merge-queue.json`, or the `rate_windows` key, so it
can be called from anywhere without contending for anything.

The randomness is injectable at the function seam (`compute_poll_delay`'s `rng`
parameter) rather than through a `--seed` flag, so a test can pin the draw and
assert the range deterministically. There is deliberately no seed flag: a seed is an
operator-facing reproducibility knob, and this value has no operator-facing reason to
be reproducible.

### build_queue — acquire

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue acquire \
  --plan-id PLAN_ID
```

Accepted flags: `--plan-id` (**required**).

Beyond `id` / `admission` / `active_count` / `waiting_count` / `queue_path`, every
result reports the cap it admitted under and the two cap reports:

| Field | Present | Meaning |
|-------|---------|---------|
| `max_slots` | always | The cap this call admitted against |
| `max_slots_source` | always | Where that cap came from (`machine_config` / `default` / `invalid` / `unreadable`) — reported unconditionally, because the value alone cannot distinguish a configured `5` from a fallback `5` |
| `max_slots_detail` | when `max_slots_source != machine_config` | Why a non-nominal source was reached; a nominal resolution has nothing to explain |
| `warnings` | **always** (empty when nothing applies) | Each entry is `{code, message}`. Consumers deduplicate on `code`, never on the message text. Two producers: `per_repo_max_slots_not_in_effect` and `cap_disagreement` |
| `per_repo_max_slots` | only when the caller's `marshal.json` carries the demoted key | `{value, in_effect: false}` — `in_effect` is stated explicitly so a reported value cannot be misread as an operative one |
| `cap_agreement` | always | `agree` / `disagree` / `unknown` — see the verdict rules below |
| `cap_compared_count` | always | The examined POPULATION (pre-existing active + waiting entries), `0` for an empty queue |
| `cap_unstamped_count` | always | How many of that population carried no usable stamp and so could not be compared |
| `cap_disagreement` | always (empty list when none) | One row per disagreeing holder: `id`, `plan_id`, `project_root`, `admitted_under_max_slots` |

`warnings` is always present so a consumer iterates it unconditionally and never
branches on whether a key is there — an optional-key shape is what makes a consumer
forget to look.

### build_queue — release

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue release \
  --plan-id PLAN_ID --id ID
```

Accepted flags: `--plan-id` (**required**), `--id` (**required** — the admission id
returned by `acquire`).

Reports `action` (`released` / `noop`), `promoted` (the FIFO-promoted waiter's id, or
null), `active_count`, `waiting_count`, `queue_path`, and the same `max_slots` /
`max_slots_source` / `max_slots_detail` cap fields as `acquire`. It does **not**
carry `warnings`, `per_repo_max_slots`, or any `cap_*` field: the demotion report and
the disagreement verdict are properties of an ADMISSION decision, and a release makes
none.

### build_queue — limit get

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue limit get
```

Accepted flags: **none** — it takes no `--plan-id`, because it reads machine-global
state belonging to no plan and the queue path resolves under the home root without
any plan resolution.

Read-only, and it writes nothing: it reads the queue through
`_locks_core.read_json_guarded`, which takes the same `O_EXCL` guard every other
access to this file takes — so the reported value can never be a torn read taken
mid-write — and returns without committing. It deliberately does NOT pass an identity
mutator to `rmw_json`: that call commits unconditionally and reports a corrupt queue
file as `{}`, so a caller merely asking for the threshold would write that `{}` back
and erase every active and waiting entry. Fields: `field` (`upper_limit_seconds`), `value`,
`source` (`queue_state` / `default_floor`), `floor_seconds` (`600`),
`ceiling_seconds` (`3600`), `reap_threshold_seconds` (`2 × value` — the age at which
the reaper reclaims an active entry), `queue_path`, plus `per_repo_value`
(`{value, in_effect: false}`) only when the caller's main-anchored
`run-configuration.json` still carries the retired `build.queue.upper_limit_seconds`.

`default_floor` is reported distinctly from `queue_state` because the fallback IS the
floor: a returned `600` could not otherwise be told apart from a configured `600`.

### build_queue — limit set

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue limit set \
  --value VALUE
```

Accepted flags: `--value` (**required**, a positive int in seconds, clamped to
`[600, 3600]`). It takes no `--plan-id`, for the same reason `limit get` does not.
The `--value` spelling is deliberate, so an operator who learned the retired
run-config setter's flag does not mispredict this one.

Written through the same serialized `rmw_json` mutation the admit/release cycle uses,
so a set cannot interleave with a release's own recompute of the same field and the
committed value is never a lost update. Fields: `field`, `value` (the clamped value
actually stored), `requested` (what was asked for), `clamped` (bool — whether the two
differ), `source` (`queue_state`), `floor_seconds`, `ceiling_seconds`,
`reap_threshold_seconds`, `queue_path`.

## Integration

| Producer / Consumer | Direction | Notation |
|---------------------|-----------|----------|
| `workflow-integration-git:integrate_into_main` | consumes | `merge_lock acquire`/`release` around the move-back |
| `phase-6-finalize/standards/branch-cleanup.md` Pre-Merge Gate | consumes | `merge_lock acquire` (FIFO poll/backoff loop on `admission: blocked`)/`check`/`release` |
| build wrappers (`_build_execute_factory`, `_pyproject_execute`) | consume | `build_queue acquire`/`release` around `execute_direct` — the in-process fallback path (unregistered / daemon-down) |
| `manage-build-server:_marshalld_scheduler` (via the D5 routing seam) | consumes | the same machine-global `build-queue.json` — the registered path (daemon-served builds) |
| `automatic-review/SKILL.md` rate-limit recovery sequence | consumes | `merge_lock rate-window claim`/`check`/`release` |
| `automatic-review/SKILL.md` Branch 3 → trigger-arm boundary | consumes | `merge_lock poll-delay` — awaits the returned `delay_seconds` once before the boundary's selector re-consult routes |
| `manage-build-server:manage_build_server config set` / `config migrate` | produces | `machine-config.json` — the machine-global `max_slots` that `build_queue acquire`/`release` resolve and report the source of; this skill only READS it |
| `_locks_core.rmw_json` | consumed by | both `build_queue` (`build-queue.json`) and `merge_lock` (`merge-queue.json` FIFO layer AND `rate_windows` claims) |

## Standards

- [scope-limited-negative-is-unknown.md](standards/scope-limited-negative-is-unknown.md) — the structural encoding of the invariant "an empty result from a scope that could not have observed the subject is `unknown`, not `absent`", the scope-limited-enumeration generalization of ADR-009 that `holder_staleness` + `release --require-stale` realize in code.
- [cwd-keyed-store-resolution-audit.md](standards/cwd-keyed-store-resolution-audit.md) — the fix-or-justify enumeration of every CWD-keyed store-resolution site against that invariant.
- [machine-global-config-scope-audit.md](standards/machine-global-config-scope-audit.md) — the derived enumeration of the sites where a config key and the state it governs sit in different anchoring tiers: a key read after a process moved its cwd away from the key's resolution root, and a key read per caller yet applied to machine-global shared state. Publishes both populations with the sweeps and the `ast` classification that re-derive them, the supplementary sweep covering the trees the inventory does not walk, and a current-state disposition for `build.queue.max_slots` and `build.queue.upper_limit_seconds`.

## Related

- `plan-marshall:script-shared` — provides `marketplace_paths.resolve_main_anchored_path` (the main-anchored resolver) and `triage_helpers` (CLI/error helpers).
- `plan-marshall:workflow-integration-git` — `integrate_into_main` consumer of the merge mutex.
- `plan-marshall:ref-code-quality` — the TOCTOU / check-then-act mitigation menu the shared core implements.
