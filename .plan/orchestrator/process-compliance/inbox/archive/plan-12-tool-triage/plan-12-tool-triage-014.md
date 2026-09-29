envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:56Z

# automatic-review's rate-window recovery cannot complete inside its dispatched leaf

**Observed (plan-12-tool-triage, finalize, PR #1653):** `plan-marshall:automatic-review` is a DISPATCHED step with a 900 s per-agent budget. With `review_rate_window_await: true` and CodeRabbit (a required bot) refusing on quota, the documented recovery claims the rate window (`merge_lock rate-window claim`, default 3600 s) and then paces a poll of the claim's expiry with a standalone `sleep 60`. In the leaf:

1. The harness rejects the standalone `sleep` (foreground sleep is blocked), so the pacing step is unexecutable as written.
2. Even with pacing allowed, a 3600 s window can never elapse inside a 900 s budget.

The leaf returned `status: blocked, reason: rate_window_await_unreachable_in_leaf` without a terminal record — the only honest option — and the item-5d completion guard then recorded `failed` / halted the FOR loop. `blocked` is not one of the recognised leaf returns (`escalate_ask` is the only no-mark carve-out), so the documented path turns a correctly-armed, known-duration wait into an attributed contract violation.

**Recurrence on retry:** after the orchestrator waited out the window in the main context and re-dispatched, the leaf stopped again at the NEXT documented pause — the jittered wake (`merge_lock poll-delay` → `delay_seconds: 1052.77`, bounds 300–1200 s) followed by a standalone `sleep` — for the same two reasons (sleep rejected; 1053 s > the 600 s Bash ceiling). Every pause in the recovery sequence is individually unreachable from a leaf, so each costs a full dispatch round-trip.

**Vacuous guard on retry:** the retried leaf again returned without a terminal record, yet `assert-step-recorded --require-terminal` returned `recorded: true, outcome: failed` — satisfied by attempt 1's stale `failed` record, not by anything the retry wrote. The item-5d guard cannot distinguish "this dispatch recorded" from "some earlier dispatch recorded"; `firing_count: 1` was the only hint.

**Also observed:**
- CodeRabbit's current refusal text ("Next included review available in 38 minutes.") did not match `rate_limit_eta_patterns` in `automatic-review/standards/coderabbit.md` — `eta` came back empty, so the claim fell back to 3600 s instead of ~2280 s.
- Sourcery (optional) returned `hard_quota` with an ETA of "2 days and 18 hours" — correctly treated as an ordinary settle.

**Suggested fix directions:** route the rate-window await to the orchestrator as an `escalate_ask`-class return (e.g. `reason: rate_window_await`, carrying `claim_expires_at`) that item 7a consumes by waiting in the main context via the await-long-running seam, then re-dispatching; and refresh the CodeRabbit ETA pattern.
