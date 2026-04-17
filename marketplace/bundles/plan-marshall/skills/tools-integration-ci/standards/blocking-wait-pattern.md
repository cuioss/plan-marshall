# Blocking-Wait Pattern

Reference for implementing blocking waits on external signals (PR comments, CI status flips, issue state changes, label updates) via `tools-integration-ci` subcommands instead of bash `sleep`.

---

## 1. Purpose

Replace bash `sleep` whenever a workflow needs to block until an external signal arrives. Claude Code's harness blocks long leading `sleep` durations, so any wait implemented as a raw shell pause (or a polled `until; do sleep …; done` loop in Bash) is unreliable and will fail in hosted runs.

All waits must be expressed as `tools-integration-ci` `wait-for-*` subcommands that run inside a Python handler on top of the shared `poll_until` framework. Shifting waits into the CI abstraction keeps the provider boundary clean, gives every caller the same timeout/interval contract, and lets the harness see a single bounded subprocess call per wait instead of a series of opaque sleeps.

---

## 2. When to Add a New `wait-for-*` Subcommand

Add a new subcommand only when **all** of the following hold:

1. **External signal** — the wait blocks on state owned by the CI provider (PR comments, CI check runs, issue state, labels, reviews). In-process state or local filesystem events do not belong here.
2. **Deterministic "done" state** — the completion predicate can be evaluated from a single API snapshot (e.g., "unresolved comment count grew", "CI status flipped from `pending` to any terminal state", "issue state is not `open`"). If "done" requires human judgement, it is not a wait — it is a review step.
3. **Reusable across workflows** — at least two callers (current or planned) need the same wait semantics. One-off waits that only one workflow ever needs should be absorbed into an existing subcommand via a new flag (or inlined into the caller's handler) rather than minted as a new top-level verb.

If any of the three criteria fail, do **not** add a new subcommand. Extend an existing one or keep the logic private to the caller.

---

## 3. Implementation Recipe on Top of `poll_until`

The shared polling primitive lives in `ci_base.py:811`:

```python
def poll_until(check_fn, is_complete_fn, *, timeout, interval) -> dict
```

`check_fn` returns `(ok: bool, data: dict)` each iteration; `is_complete_fn(data) -> bool` decides when to stop. The helper returns `{'timed_out', 'duration_sec', 'polls', 'last_data'}` plus `'error'` on fetch failure.

Model new handlers after the canonical `cmd_pr_wait_for_comments` at `github_ops.py:780`. The skeleton is:

```python
def cmd_pr_wait_for_comments(args):
    # 1. Snapshot baseline from a single provider call.
    initial = fetch_pr_comments_data(args.pr_number, unresolved_only=True)
    baseline = int(initial.get('unresolved') or 0)

    # 2. check_fn: fetch latest snapshot, propagate fetch errors.
    def check_fn():
        snap = fetch_pr_comments_data(args.pr_number, unresolved_only=True)
        if snap.get('status') != 'success':
            return False, {'error': 'fetch failed'}
        return True, {'unresolved': int(snap.get('unresolved') or 0)}

    # 3. is_complete_fn: pure predicate over snapshot data.
    def is_complete_fn(data):
        return int(data.get('unresolved', 0)) > baseline

    # 4. Delegate the loop.
    result = poll_until(check_fn, is_complete_fn,
                       timeout=args.timeout, interval=args.interval)

    # 5. Shape the response dict.
    final_count = int(result['last_data'].get('unresolved', baseline))
    return {
        'status': 'success',
        'operation': 'pr_wait_for_comments',
        'pr_number': args.pr_number,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_count': baseline,
        'final_count': final_count,
    }
```

Every new handler must: (a) snapshot the baseline exactly once before polling; (b) keep `check_fn` side-effect-free apart from the provider read; (c) keep `is_complete_fn` a pure predicate on `data`; (d) always return `operation`, `timed_out`, `duration_sec`, `polls`, plus the baseline/final snapshot fields that let callers diff what changed.

---

## 4. Timeout / Interval Guidance

Defaults come from `ci_base.py:224-225`:

- `DEFAULT_CI_TIMEOUT = 300` seconds
- `DEFAULT_CI_INTERVAL = 30` seconds

Register both `--timeout` and `--interval` on the subcommand's argparse parser with these defaults (see `ci_base.py:475` for the `pr wait-for-comments` registration as a template). **Never hard-code a timeout or interval inside the handler body** — the handler must pass `timeout=args.timeout, interval=args.interval` straight through to `poll_until`.

Callers that need a different ceiling pass `--timeout` explicitly. For example, `workflow-pr-doctor` supplies its configured `review_bot_buffer_seconds` instead of the default 300 so review bots have the full buffered window to respond. Callers that need faster feedback for local iteration can shrink `--interval`, but the default stays at 30 seconds to keep API quota pressure predictable.

---

## 5. Subcommand Catalog

| Subcommand | When to use | Canonical caller |
|------------|-------------|------------------|
| `pr wait-for-comments` | New review-bot feedback needs to arrive before triage continues. | `workflow-pr-doctor` Automated Review Lifecycle, Step 2 |
| `ci wait-for-status-flip` | PR CI status must transition from `pending` to a terminal state (`success` / `failure`). | `pr-doctor` after pushing fixes, before re-reading CI results |
| `issue wait-for-close` | Automation blocks until an issue's state flips from `open` (triage / merge-queue closes it). | Automation that gates follow-up work on issue closure |
| `issue wait-for-label` | Automation gates on a label being added or removed (e.g., `ready-for-review`, `blocked`). | Review-gate automations that watch label state |

All four subcommands follow the recipe in section 3 and honour the timeout/interval contract in section 4.
