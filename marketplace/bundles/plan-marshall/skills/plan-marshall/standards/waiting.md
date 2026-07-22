# Waiting for an External Event

The target-neutral standard for the wait class: work that cannot proceed until something outside this process reaches a terminal state. It states **when** to wait, **who** may hold a wait, **what a waiter must be able to observe**, and **how** the wait is realised on a target that has no background-watch mechanism.

This is the policy half of the waiting capability. The mechanism half — the primitive that actually holds a bounded wait over a concrete, inspectable observable — is a `Runtime` operation that a target may decline; see [`platform-runtime`](../../platform-runtime/SKILL.md) and its [`standards/no-op-policy.md`](../../platform-runtime/standards/no-op-policy.md). The split, and the reasoning that produced it, is recorded in **ADR-011** (`doc/adr/011-The_waiting_capability_is_a_hybrid_target-neutral_policy_over_a_declinable_runtime_primitive.adoc`).

Every realisation below is expressed as **"wait until condition C holds, or one of its terminal-failure states."** This document deliberately names no target-specific primitive and uses no event-stream vocabulary: a reader on any target can follow it end to end.

## When to wait — the wait-class signal set

A signal belongs to the wait class when its terminal state is produced by an external system on its own schedule, and no amount of local work brings it closer. The recurring members:

| Signal | Terminal condition |
|--------|--------------------|
| Remote CI run | The run reaches a terminal conclusion for the settled commit |
| Merge queue | The change is merged, or is ejected from the queue |
| Review-bot comments | The bot reports its review complete for the settled commit |
| Static-analysis compute job | The engine's analysis task for the submitted commit finishes |
| Build-server long poll | The submitted build job reaches a terminal job status |

Anything not in this class is not a wait — it is either local work to run synchronously, or a poll that should be replaced by the signal's own terminal-state query. A bare timed sleep is never a member: sleeping is not waiting for a condition, it is guessing at one.

## The main loop owns waiting — leaves never do

**Only the main execution loop may hold a wait. A dispatched leaf must not.**

The reasoning is about reaping, not about convenience. A dispatched leaf runs inside an envelope that the harness may reap; once reaped, **the leaf cannot be resumed** — its context is gone and nothing re-enters it to collect a result. A wait held by a leaf therefore loses the result outright when the reap lands mid-wait, and the loss is silent: the work the leaf was waiting on may well have completed successfully with nobody left to observe it. The main-context orchestrator has the opposite property: it can re-enter, so a wait it holds is recoverable by re-issuing the wait.

The exact lifetime cap on a dispatched envelope is **unverified** — no measurement establishes how long a leaf may run before it is reaped, and none should be assumed. **The design must not depend on that number.** The rule is therefore structural rather than budgetary: waiting is placed where re-entry is possible, so correctness does not rest on an unknown bound. A leaf that discovers it needs a wait returns a signal to the orchestrator and stops; it does not shorten the wait and hope to fit.

## Silence is not success — the failure-signature coverage rule

**A waiter's terminal-state set MUST include the failure signatures, never only the happy path.**

The condition a waiter awaits is not "the good outcome arrived." It is "the observed thing reached *any* terminal state," and the terminal states include:

- the awaited success,
- **failed** — the external system finished and the outcome is negative,
- **cancelled** — the work was withdrawn before producing an outcome,
- **timed out** — the external system itself gave up,
- **killed** — the work was terminated externally rather than completing.

A waiter that watches only for the success signature cannot distinguish "not finished yet" from "finished badly," so it will read a failure as continued waiting and, at the end of its bound, report the absence as a pass. That inversion is the characteristic defect of this class.

The corollary is the reading rule: **an absent signal is `unknown`, never `passed`.** A waiter that cannot substantiate a terminal state reports that it could not — an explicit unknown the caller must branch on. This is the same fail-closed posture ADR-009 establishes for status surfaces: a positive is only ever emitted when it is substantiated.

## The tiered realisation

Three tiers, in descending order of what the target supports. Every tier satisfies the policy above; they differ only in mechanics and in what a reap costs.

**Tier 1 — a background-watch primitive, where the target has one.** The wait is held out-of-band while the main loop stays responsive, and the terminal state arrives as a completion signal. It covers the single-completion case (one condition, one terminal state) as well as the several-conditions case, in which each condition is tracked independently and each terminal arrival is handled once — a repeat notification for an already-handled condition is a no-op, while a first notification for a not-yet-handled condition is real work. Tier 1 is a **known-lossy** mechanism: the loss is *detected* by the terminal-state coverage rule above, not prevented by the primitive.

Tier 1 is **agent-level**. Where a target offers it, it is driven by the execution loop itself, not by a call into the runtime: the affordance has no programmatic surface a runtime operation could register against. That is why the `Runtime` waiting operation does **not** implement this tier — see tier 2.

**Tier 2 — a bounded wait over a concrete observable.** The caller blocks until the observed thing reaches a terminal state or the bound expires. Available on every target, since it needs nothing but the ability to query the observed thing's terminal state. It costs responsiveness — the caller is blocked for the duration — but it is fully correct.

**This is the `Runtime` waiting operation's implementing path.** The operation names *what* is being awaited as a concrete, inspectable observable drawn from a closed set — never an opaque condition, which nothing running outside the execution loop could evaluate — and returns a normalised terminal outcome, or an explicit non-terminal pending when the bound expires. A target whose runtime cannot hold such a wait declines it, and the decline's first alternative is this same tier reached directly: the observed thing's own bounded-wait surface, invoked in-turn.

**Tier 3 — checkpoint and re-dispatch.** The caller records enough state to resume, returns, and is re-entered later to re-issue the wait. **This tier is correct even under worst-case reaping**, because no wait is held across the reap boundary at all: the wait is re-established on re-entry from persisted state. It is the fallback of last resort and the one tier that assumes nothing about the target or the harness.

A target whose `Runtime` waiting operation declines returns `status: no-op` with a `reason` and an `alternative`, and the alternative names tier 2 reached directly, or tier 3. Per the No-Op Policy, the caller logs the reason, applies the alternative, and **continues** — a declined wait never fails a workflow.

## The selected tier must be recoverable from the log

**Every wait-class realisation MUST make the mechanism it actually ran on recoverable from the log.** "Was the tiered realisation used consistently, and did a realisation silently degrade from one tier to a lower one?" must be answerable from a log query alone, not inferred from the code path.

The shared field is the closed **`mechanism`** vocabulary: each wait arm names the mechanism it selected — the CI-wait arm's `seed_only` / `watch_tail` / `poll_fallback`, the build arm's `daemon_longpoll` / `in_process_fallback` — so one `mechanism=` query spans every arm. A **degrade** from a tier-1 realisation to a tier-2 one (a watch-tail wait that fell through to the bounded poll, a routed build that fell back in-process) is a **recordable event, not a silent equivalence**: it is logged at `WARNING` so it is distinguishable from the tier-1 realisation it stood in for. A realisation that runs a lower tier without recording it violates this rule — silence about the degrade is the characteristic defect the coverage rule above forbids, applied to the mechanism selection itself.

The concrete record shape (the `[WAIT]` work-log line, its field set, and which party declares the caller-only `dispatch` field) is owned by [`workflow/await-long-running.md`](../workflow/await-long-running.md) § Output — this clause states the requirement once and does not restate the record shape.

## Bounded polling and the build-server relationship

The build-server client is the worked example of a wait whose cost under reaping is already minimal, and it shows why a bounded server-side poll is not backgrounded.

The daemon **separates the wait from the work**: the build runs in the daemon's supervised child process, while the caller holds only a bounded long poll for the result. The two are different processes, so a reaped *wait* costs exactly **one re-poll** — the caller re-issues the wait and re-attaches to the still-running job — and never the whole build. Backgrounding such a wait would add a lossy layer on top of a mechanism that is already cheap to lose and cheap to recover.

**A daemon wait is therefore never backgrounded.** Re-issue the poll instead. The same shape generalises: whenever the waiting process and the working process are separable, separate them, and hold only the cheap, re-issuable half.

The daemon also illustrates the coverage rule concretely — it reports an externally-terminated child under its own terminal status rather than folding it into a generic failure or, worse, into silence.

## Budgets are bounds, not verdicts

A wall-clock budget answers "how long am I willing to hold this wait," and **nothing else**. It never answers "did the awaited thing succeed."

**Budget exhaustion yields an explicit unknown / pending outcome that the caller must act on — never an implicit pass.** When the bound expires, the waiter reports that the condition had not reached a terminal state within the bound, and the caller decides what to do: re-issue the wait, escalate, or proceed with the uncertainty recorded. What it must not do is treat the expiry as evidence of anything about the outcome. This is the same fail-closed shape as the silence-is-not-success rule and as ADR-009 — an unsubstantiated positive is never emitted.

The finalize CI wait is the standard's **first intended consumer**: a fixed wall-clock budget on the CI wait is a bound on the orchestrator's patience, and its expiry means "CI has not concluded yet," which is an actionable pending state — not "CI passed." A budget chosen too small produces more pending outcomes; it never produces a wrong verdict, because the budget has no verdict to give.

## Scope

No existing waiting call site is migrated onto the `Runtime` waiting operation by this standard. The seams that wait today — the detach-and-notify orchestration seam, the CI abstraction's bounded wait verbs, the finalize CI wait, and the build-server long poll — continue to behave exactly as they do. This document states the policy they are measured against; migrating them onto the operation is separate work.

## Related

- **ADR-011** — the decision this standard realises: waiting is a target-neutral policy over a declinable runtime primitive, and the target-specific-skill route is rejected.
- [`workflow/await-long-running.md`](../workflow/await-long-running.md) — the shipped detach-and-notify orchestration seam, the tier-1 realisation (agent-level, with a tier-2 fallback).
- [`platform-runtime/standards/no-op-policy.md`](../../platform-runtime/standards/no-op-policy.md) — the decline contract (`reason` plus `alternative`) and the caller's obligation to continue.
- [`tools-integration-ci/standards/blocking-wait-pattern.md`](../../tools-integration-ci/standards/blocking-wait-pattern.md) — the bounded wait verbs, the tier-2 realisation available on every target.
- [`build-server-client/SKILL.md`](../../build-server-client/SKILL.md) — the submit/wait split behind the bounded-poll relationship above.
- [`persona-plan-marshall-agent/standards/tool-usage-patterns.md`](../../persona-plan-marshall-agent/standards/tool-usage-patterns.md) § "No sleep for external waits" — the always-loaded floor's pointer to this standard.
