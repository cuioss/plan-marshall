# Blocking-Wait Pattern

Reference for implementing blocking waits on external signals (PR comments, CI status flips, issue state changes, label updates) via `tools-integration-ci` subcommands instead of bash `sleep`.

---

## 1. Purpose

Replace bash `sleep` whenever a workflow needs to block until an external signal arrives. The host platform's harness blocks long leading `sleep` durations, so any wait implemented as a raw shell pause (or a polled `until; do sleep …; done` loop in Bash) is unreliable and will fail in hosted runs.

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

Callers that need a different ceiling pass `--timeout` explicitly. For example, `workflow-pr-doctor` supplies the `review_bot_buffer_seconds` value it reads from the `plan-marshall:automatic-review` step's params in the plan-local manifest step-params snapshot, instead of the default 300, so review bots have the full buffered window to respond. The `--timeout` pass-through contract is unchanged — the value is just sourced from the manifest step-params snapshot rather than a flat config field. Callers that need faster feedback for local iteration can shrink `--interval`, but the default stays at 30 seconds to keep API quota pressure predictable.

---

## 5. Subcommand Catalog

| Subcommand | When to use | Canonical caller |
|------------|-------------|------------------|
| `pr wait-for-comments` | New review-bot feedback needs to arrive before triage continues. | `workflow-pr-doctor` Automated Review Lifecycle, Step 2 |
| `ci wait-for-status-flip` | PR CI status must transition from `pending` to a terminal state (`success` / `failure`). | `pr-doctor` after pushing fixes, before re-reading CI results |
| `issue wait-for-close` | Automation blocks until an issue's state flips from `open` (triage / merge-queue closes it). | Automation that gates follow-up work on issue closure |
| `issue wait-for-label` | Automation gates on a label being added or removed (e.g., `ready-for-review`, `blocked`). | Review-gate automations that watch label state |

All four subcommands follow the recipe in section 3 and honour the timeout/interval contract in section 4.

---

## 6. The seed-then-watch CI-run wait (distinct from the `poll_until` snapshot-diff waits)

The `ci wait` handler (`cmd_ci_wait`, GitHub `_github_ci.py` / GitLab `gitlab_ops.py`) waits for a whole CI run to reach a terminal conclusion. That is a **different shape** from the section-3 snapshot-diff waits: those block until a single scalar snapshot *changes* (unresolved-comment count grows, status flips), and a fixed-interval `poll_until` re-fetch is the right tool. A CI run instead has a **known-busy window** — it will be running for roughly as long as it ran last time — so polling `pr checks` every 30 s from second zero burns API quota during a window where the answer cannot yet be "done". `cmd_ci_wait` therefore uses a two-stage **seed-then-watch** wait instead of the fixed-interval loop:

1. **p50 first-sleep seed.** Before doing anything, read the historical p50 (median) of the last N observed successful `ci:wait` durations via `run_config ci-duration p50 --command ci:wait` (see [`manage-run-config` SKILL.md](../../manage-run-config/SKILL.md) § "ci-duration record / p50") and sleep that seed **once**, bounded by `--timeout`. The seed is skipped when the window is empty (a `null` p50). This front-loads the wait through the window where CI is known to still be busy, with a single sleep rather than a series of polls.

2. **Terminal-state watch-verb tail.** Delegate the tail to the provider's **purpose-built terminal-state watch verb** — `gh run watch --exit-status` (GitHub) / `glab ci status --wait` (GitLab) — which blocks on the provider's own ETag/304-conditional signal until the run concludes. This is **never a hand-rolled sleep loop** (Claude Code issue #65985): the watch verb owns the waiting, so there is no `while not done: sleep` in the handler. Each provider isolates the watch verb behind a private, test-mockable subprocess seam (`_watch_run` / `_watch_pipeline`).

3. **Record back into the window.** On a natural (non-timeout) **success** completion, record the observed wall-clock `duration_sec` into the p50 window via `run_config ci-duration record --command ci:wait`, closing the adaptive loop so the next wait's seed tracks real CI durations.

**Fallback.** When CI has not yet registered a watchable run (empty checks, or wait-state checks whose links carry no resolvable run id), the handler falls back to the section-3 `poll_until` framework for the remaining budget — preserving the "keep waiting until checks appear, then time out" behaviour. `poll_until` remains the sanctioned framework; the watch verb is the primary tail for the common case where the run is already present.

**Return contract is additive-only.** `cmd_ci_wait` preserves `final_status`, `duration_sec`, `failing_checks`, `wait_outcome`, `run_id`, `head_sha`, and the `deadline_exceeded` timeout envelope — so `ci_complete_precondition.py` consumes it without modification — and additionally carries the selected `mechanism` (`seed_only` / `watch_tail` / `poll_fallback`) on both the success and `deadline_exceeded` return paths, so the orchestrator can reconcile the wait mechanism from the command result (see [`await-long-running`](../../plan-marshall/workflow/await-long-running.md) § Output).

**Detach behind the `await-long-running` seam.** The orchestrator does not block synchronously on the whole CI wait: it detaches the `ci wait` call behind the shared [`await-long-running`](../../plan-marshall/workflow/await-long-running.md) detach-and-notify seam (the remote-CI-wait consumer), backgrounding it and waking on the completion notification. The p50 seed + watch-verb tail described here is the wait's *internal* mechanism; the seam is how the orchestrator *consumes* it without babysitting.

This pattern is intentionally **not** added to the section-5 subcommand catalog: it is the internal mechanism of the existing `ci wait` verb, not a new `wait-for-*` subcommand. The section-2 "when to add a new subcommand" test does not apply — no new verb is minted.
