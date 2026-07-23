---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Await Long-Running Workflow (detach-and-notify seam)

The single shared orchestration seam for a long-running orchestrator-tier call: instead of the orchestrator blocking synchronously on a remote-CI wait, it **detaches** the call (runs it in the background) and **wakes on the completion notification** — the "Hollywood principle" (don't call us, we'll call you). On wake it reads the wrapper's compact TOON, never the raw log flood, and never a hand-rolled poll loop.

The governing policy this seam realizes is [`../standards/waiting.md`](../standards/waiting.md) — the target-neutral waiting standard (when to wait, the main-loop-owns-waiting rule, the silence-≠-success terminal-state coverage rule, the tiered realization, and the budget-is-a-bound rule). This document is the concrete recipe; that document is the policy it answers to.

This seam is **orchestration guidance the main-context orchestrator follows** — it is not a script that "runs the orchestrator's build". The orchestrator is the LLM following the persona + workflow docs; this document is the recipe it applies whenever a remote-CI wait (or the phase-6 finalize barrier) is about to block. Both wait-class consumers share the same seam; only the parameters differ.

**The build consumer does NOT use this detach-and-notify seam.** A long-running orchestrator-tier build (`compile` / `module-tests` / `verify` / `coverage` / `quality-gate` beyond the per-task Bash ceiling) is instead routed to the `marshalld` build server through `build-server-client` submit/wait — the daemon separates the WAIT from the WORK, so a harness-reaped wait costs one re-poll rather than the whole build. See § "Build consumer — routes through build-server-client" below; the `run_in_background` detach + kill-classification rungs the build arm previously carried are superseded by the daemon's first-class `killed` status.

The wake primitive (the background-completion notification) is **Claude-specific** — Claude Code is the only tested runtime — but the Claude-specificity is **contained behind this seam**: the fallback below degrades to today's synchronous blocking call when the background primitive is unavailable, so the two wait-class consumers carry no runtime-specific branching of their own.

## Build consumer — routes through build-server-client

An orchestrator-tier build is owned by the `marshalld` build server, not this detach-and-notify seam. The build-execute routing seam ([`../../script-shared/scripts/build/_build_execute_factory.py`](../../script-shared/scripts/build/_build_execute_factory.py), D5) does the routing at the build-wrapper level: when the project is **registered AND the daemon is ready**, the build is submitted to marshalld and the caller performs one **server-side bounded long-poll** for its result via the [`build-server-client`](../../build-server-client/SKILL.md) `submit` / `wait` verbs.

The two properties that make this replace the `run_in_background` build detach:

- **The wait and the work are separate processes.** The build runs in the daemon's supervised child; the caller only holds a bounded `wait`. A harness reap of the `wait` therefore costs exactly **one re-poll** (the caller re-issues `wait`, re-attaching via the change-ledger `job_id`) — never the whole build. This is the residual pain the old `run_in_background` build detach could not remove: a reaped background build lost the entire build.
- **`killed` is a first-class daemon status.** The daemon classifies an externally-killed child as `killed` ("externally killed — not flaky, do not blind-retry") and returns it over `wait`. This **supersedes** the build arm's former deterministic kill-detection classifier (`manage-change-ledger classify-outcome` over the missing-ledger-row / zero-output signature): the build arm no longer needs it, because the daemon reports the kill directly. `classify-outcome` remains only for any residual detached-build path that is not daemon-served.

When the project is **unregistered or the daemon is down**, the routing seam falls back to an in-process build under the single machine-global build-queue slot and records the degradation reason (D5). This fallback is owned at the build-wrapper level, not here; this seam is not re-entered for the build consumer.

Do NOT `run_in_background` or `sleep` the daemon `wait` — the daemon holds the long-poll server-side, and a reaped wait is recovered by re-issuing `wait`, not by backgrounding it. See [`build-server-client/SKILL.md`](../../build-server-client/SKILL.md) for the submit/wait/ping/preflight contract and the status-TOON guarantees.

## Consumers

| Consumer | What is detached | Completion signal |
|----------|------------------|-------------------|
| **remote-CI wait** | The provider CI-wait handler (`cmd_ci_wait` for GitHub / GitLab) that seeds its first sleep from the p50 window then tails the provider's terminal-state watch verb | Background-completion notification → wait handler's return TOON (`final_status`, `duration_sec`, `failing_checks`) |
| **finalize-wait barrier** | The phase-6 concurrent wait barrier — the three per-signal waits ({CI, review-bot comments, Sonar CE}) detached concurrently off one settled HEAD, coordinated by the `ci barrier` per-signal-proceed / re-settle verb | Background-completion notification on ANY signal's state transition (per-signal-proceed) OR barrier budget exhaustion → the `ci barrier` decision TOON (`barrier_status`, `proceed`/`pending`/`failed`/`affected`) |

Neither wait-class consumer consumes a local build slot, so both skip any build-queue rung. (The build consumer, which does hold a machine-global slot, is served by the routing seam described above — not here.)

### Finalize-wait barrier consumer specifics

The finalize-wait barrier (see [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) § "Wait-region: the concurrent barrier off one settled HEAD") is a **wait-class** consumer — it consumes no local build slot. It differs from a single remote-CI wait in three ways:

- **Fan-out concurrency**: the three per-signal arms are detached **concurrently** off the one settled HEAD, so the barrier's wall time approaches `max(signal)` rather than `sum(signal)`. Each arm reuses its own existing ratchet (the CI arm reuses the p50-seeded `cmd_ci_wait`; see the remote-CI wait row).
- **Wake-on-transition, per-signal-proceed**: the barrier wakes on ANY arm's state transition (a signal reaching a terminal state) — NOT only when all three settle — so the orchestrator proceeds past each settled arm independently. It also wakes on **budget exhaustion**. On each wake it reads the compact `ci barrier` decision TOON (never the raw poll flood) and advances the arms named in `proceed` while continuing to await those in `pending`.
- **Bounded re-settle re-entry**: when a `barrier_status: re_settle` decision names `affected` arms (a fix pushed after barrier entry advanced HEAD), the orchestrator re-detaches only those affected arms against the new settled HEAD — never a full finalize replay. This converges in ≤1–2 iterations (see the phase-6 wait-region narrative).
- **Multi-arm notification lifecycle — per-arm gate, re-arm while pending**: because the barrier wakes per-signal, MULTIPLE legitimate completion notifications arrive during one barrier — one per arm as each reaches a terminal state (`settled` or `failed`, the `proceed` / `failed` buckets). The single-gate idempotency contract of step (d) (one `build-busy` state → handle-and-clear-once in step (e)) is NOT sufficient here on its own: a naïve single gate cleared on the FIRST arm's completion would treat every LATER arm's genuine completion as an already-handled duplicate reminder and drop it. The barrier consumer therefore gates per-arm, not once for the whole barrier: it tracks which arms it has already handled (the `proceed` / `failed` names it has already consumed) and, on each wake, handles ONLY the newly-terminal arms named in that wake's decision TOON that it has not yet handled. Equivalently, it **re-arms** the `build-busy` state after each per-arm handling **whenever the decision TOON still reports a non-empty `pending` bucket** (more arms are still coming), and only performs the final state-gated clear once the decision reaches a terminal `barrier_status` (`complete`, or a `failed`/`re_settle` the orchestrator acts on) with an empty `pending` bucket. A repeated "still running" reminder for an arm already handled remains a no-op (the Claude Code issue #11190 leak guard); the distinction is between a repeat of an ALREADY-handled arm (no-op) and a fresh completion of a not-yet-handled arm (handle it), which the per-arm handled-set — not a single whole-barrier gate — is what disambiguates.

The **synchronous-blocking fallback (step (g))** applies unchanged: when the background primitive is unavailable, the barrier degrades to awaiting each arm's wait **inline** at its resolved timeout — i.e. the pre-detach serial blocking behaviour — still bracketed by the build-busy set/clear. The Claude-specific wake primitive stays contained behind this seam; the barrier consumer carries no runtime-specific branch of its own.

## Parameters

| Parameter | Description |
|-----------|-------------|
| `plan_id` | Plan identifier — forwarded to every `manage-status` / `platform-runtime` call below. |
| `consumer` | `ci-wait` or `finalize-barrier` — selects the completion-TOON shape. `finalize-barrier` follows the same rungs as `ci-wait` but wakes per-signal (see § "Finalize-wait barrier consumer specifics"). The build consumer is served by `build-server-client` submit/wait (see § "Build consumer — routes through build-server-client") and is not a value here. |
| `command` | The CI-wait handler invocation to run detached. |
| `bash_timeout_seconds` | The architecture-resolved timeout, used ONLY on the fallback synchronous path (step g). |

## Recipe

The seam is a fixed sequence applied by the two wait-class consumers. Neither consumes a local build slot.

### (b) Set and live-push the `build-busy` title-token

Persist the `build-busy` state AND live-push the 🔨 glyph to the terminal so the title surfaces the busy symbol for the whole detached window. Both calls are **best-effort** — a failure never aborts the detached call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status title-token set \
  --state build-busy --plan-id {plan_id}
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --plan-id {plan_id} --icon 🔨
```

The live `/dev/tty` OSC write is the only mechanism that repaints the terminal during a blocking/detached window — the bare `title-token set` alone writes `status.json` and is invisible until the next repaint. See [`persona-plan-marshall-agent` § build-busy bracketing](../../persona-plan-marshall-agent/SKILL.md#hard-rules-never-override) for the shared title-surface seam contract.

### (c) Invoke the command detached (background primitive)

Run the CI-wait handler with the Claude background primitive — the Bash `run_in_background: true` parameter — so the orchestrator does NOT block on it:

```text
Bash(command="{command}", run_in_background: true)
```

`run_in_background` is a **known-lossy primitive**: the harness kills backgrounded jobs with zero output, and the loss is **detected on the wake path (steps d/e), not prevented**.

Because THIS is the detached path, the orchestrator MUST declare it to the wait handler by passing `--dispatch detached` on the `ci-wait` invocation. The wait handler cannot self-observe whether it was launched detached or inline — `--dispatch` is the one field the caller alone knows, and it is recorded on the handler's `[WAIT]` mechanism-selection record (see § Output). Omitting it records `dispatch=undeclared`, which makes a caller that skipped the declaration visible in the log rather than laundering it into a plausible default.

Do NOT poll for completion and do NOT `sleep`/`wait` on the backgrounded job — the completion notification is the wake signal (step d).

### (d) On the completion notification, check the state gate FIRST

The persisted `build-busy` title-token state IS the **"not-yet-handled" gate**, and it runs BEFORE any outcome work. When the background-completion notification arrives, the orchestrator reads the current state, and the gate — not the arrival of a reminder — decides whether to act:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Read `title_token` from the returned TOON, then branch:

- **`title_token == build-busy` (state present → not yet handled)** — this is the first handling of the completion. Proceed to step (e): handle the outcome exactly once, clear the state, and push the restored repaint.
- **`title_token` absent (state already cleared → already handled)** — this is a **repeated "still running" reminder**, not a fresh completion. **No-op**: do NOT read any TOON, do NOT re-clear. Gating BEFORE the handling is what makes the repeat a true no-op. An un-gated reminder that re-runs the handling on every repeat is the failure mode behind Claude Code issue #11190, where a leaked reminder re-fired thousands of tokens. The title-token-state gate is the idempotency mechanism that makes the handling fire exactly once regardless of how many reminders arrive.

### (e) Handle the outcome once (state-present branch only), then clear

This step runs ONLY on the state-present branch of step (d). The outcome handling branches by `consumer`:

- **`ci-wait`** — read the wait handler's return TOON directly: `final_status`, `duration_sec`, and `failing_checks` (per the Consumers table above).

- **`finalize-barrier`** — read the `ci barrier` decision TOON directly: `barrier_status` and the `proceed` / `pending` / `failed` / `affected` buckets, applying the per-arm handled-set gating from § "Finalize-wait barrier consumer specifics" (re-arm while `pending` is non-empty; final clear only at a terminal `barrier_status` with an empty `pending` bucket).

After the consumer-specific handling, clear the state and push the restored repaint:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status title-token clear \
  --plan-id {plan_id}
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --plan-id {plan_id}
```

The plain `session push-title-token` (no `--icon`) repaints to the current process icon (e.g. ➤ active).

All four title-surface operations (set / clear / both pushes) are **best-effort**, mirroring `merge_lock` — a failure of any one never aborts the wrapped operation.

### (g) Fallback — synchronous blocking call

When the Claude background primitive is unavailable (a non-Claude runtime, or the `run_in_background` parameter is not honoured), the seam degrades to **today's synchronous blocking call**: run `{command}` **inline** at `timeout: bash_timeout_seconds * 1000` (the architecture-resolved envelope's `bash_timeout_seconds`), still bracketed by the build-busy set (step b) and the clear (step e). On this inline path the orchestrator MUST pass `--dispatch inline` on the `ci-wait` invocation — the mirror of step (c)'s `--dispatch detached` — so the handler's `[WAIT]` record names the synchronous realisation rather than recording `dispatch=undeclared`. On the synchronous path the completion is the Bash call's own return, so the clear is unconditional (there is no reminder to gate against) — but keeping the state-read gate is harmless and preserves one code path.

The synchronous fallback is behaviourally identical to the pre-detach model; it exists so the Claude-specific wake primitive stays contained behind this seam rather than leaking a runtime branch into either consumer.

## Related

- [`build-server-client` SKILL.md](../../build-server-client/SKILL.md) — the submit/wait/ping/preflight client contract the build consumer routes through (replacing the build arm's former detach on this seam).
- [`persona-plan-marshall-agent` SKILL.md](../../persona-plan-marshall-agent/SKILL.md) — the build-busy bracketing contract that routes orchestrator-tier long-running calls through this seam (cross-reference, not duplication) and owns the shared title-surface seam semantics.
- [`phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md) — the `execution_tier=orchestrator` bullet names the orchestrator-tier build consumer, preserving the "not run inline by the step body" invariant.
- [`tools-integration-ci/standards/blocking-wait-pattern.md`](../../tools-integration-ci/standards/blocking-wait-pattern.md) — the remote-CI wait's seed-then-watch pattern; the orchestrator detaches the whole CI wait behind this seam.

## Output

Orchestration-guidance seam followed by the main-context orchestrator. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<detached {consumer} completed: {short outcome}>"
mechanism: seed_only | watch_tail | poll_fallback
```

The orchestrator emits this shape when the seam is wrapped in a `Task: execution-context-{level}` dispatch; it carries the `ci-wait` arm's `mechanism` stamp back on the return so the orchestrator can reconcile which mechanism the detached wait actually ran on.

The mechanism-selection evidence is the `[WAIT]` work-log record written by the `ci-wait` handler itself — on **every resolved wait**, on both the inline (step g) and the detached (step c) path — NOT by this seam's own prose transitions. The record names `consumer`, the resolved `mechanism` (`seed_only` / `watch_tail` / `poll_fallback`), the caller-declared `dispatch` (`detached` / `inline` / `undeclared`), the `target`, and the `outcome`; a degrade to `poll_fallback` is recorded at `WARNING` so a silent fallback from the terminal-state watch tail is greppable. The seam's detach/wake/clear steps are NOT themselves a log source — the wait handler's record is the single mechanism-selection evidence, and the live `/dev/tty` title repaints remain the visual signal only.
