---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Await Long-Running Workflow (detach-and-notify seam)

The single shared orchestration seam for any long-running orchestrator-tier call: instead of the orchestrator blocking synchronously on a build/verify command or a remote-CI wait, it **detaches** the call (runs it in the background) and **wakes on the completion notification** — the "Hollywood principle" (don't call us, we'll call you). On wake it reads the wrapper's compact TOON, never the raw log flood, and never a hand-rolled poll loop.

This seam is **orchestration guidance the main-context orchestrator follows** — it is not a script that "runs the orchestrator's build". The orchestrator is the LLM following the persona + workflow docs; this document is the recipe it applies whenever a resolved canonical command carries `execution_tier=orchestrator` (a build/verify longer than the per-task Bash ceiling) or a remote-CI wait is about to block. Both consumers share the same seam; only the parameters differ.

The wake primitive (the background-completion notification) is **Claude-specific** — Claude Code is the only tested runtime — but the Claude-specificity is **contained behind this seam**: the fallback below degrades to today's synchronous blocking call when the background primitive is unavailable, so the two consumers carry no runtime-specific branching of their own.

## Consumers

| Consumer | What is detached | Build-queue slot | Completion signal |
|----------|------------------|:----------------:|-------------------|
| **build/verify** | The architecture-resolved wrapper command (`compile` / `module-tests` / `verify` / `coverage` / `quality-gate`) whose resolved envelope carries `execution_tier=orchestrator` | Yes — acquire before, release after | Background-completion notification → wrapper's compact result TOON |
| **remote-CI wait** | The provider CI-wait handler (`cmd_ci_wait` for GitHub / GitLab) that seeds its first sleep from the p50 window then tails the provider's terminal-state watch verb | No — a CI wait consumes no local build slot | Background-completion notification → wait handler's return TOON (`final_status`, `duration_sec`, `failing_checks`) |
| **finalize-wait barrier** | The phase-6 concurrent wait barrier — the three per-signal waits ({CI, review-bot comments, Sonar CE}) detached concurrently off one settled HEAD, coordinated by the `ci barrier` per-signal-proceed / re-settle verb | No — a wait consumes no local build slot | Background-completion notification on ANY signal's state transition (per-signal-proceed) OR barrier budget exhaustion → the `ci barrier` decision TOON (`barrier_status`, `proceed`/`pending`/`affected`) |

### Finalize-wait barrier consumer specifics

The finalize-wait barrier (see [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) § "Wait-region: the concurrent barrier off one settled HEAD") is a **wait-class** consumer — it consumes no local build slot, so it skips the build-queue rungs (a) and (f) exactly like the remote-CI wait. It differs from a single remote-CI wait in three ways:

- **Fan-out concurrency**: the three per-signal arms are detached **concurrently** off the one settled HEAD, so the barrier's wall time approaches `max(signal)` rather than `sum(signal)`. Each arm reuses its own existing ratchet (the CI arm reuses the p50-seeded `cmd_ci_wait`; see the remote-CI wait row).
- **Wake-on-transition, per-signal-proceed**: the barrier wakes on ANY arm's state transition (a signal reaching a terminal state) — NOT only when all three settle — so the orchestrator proceeds past each settled arm independently. It also wakes on **budget exhaustion**. On each wake it reads the compact `ci barrier` decision TOON (never the raw poll flood) and advances the arms named in `proceed` while continuing to await those in `pending`.
- **Bounded re-settle re-entry**: when a `barrier_status: re_settle` decision names `affected` arms (a fix pushed after barrier entry advanced HEAD), the orchestrator re-detaches only those affected arms against the new settled HEAD — never a full finalize replay. This converges in ≤1–2 iterations (see the phase-6 wait-region narrative).

The **synchronous-blocking fallback (step (g))** applies unchanged: when the background primitive is unavailable, the barrier degrades to awaiting each arm's wait **inline** at its resolved timeout — i.e. the pre-detach serial blocking behaviour — still bracketed by the build-busy set/clear. The Claude-specific wake primitive stays contained behind this seam; the barrier consumer carries no runtime-specific branch of its own.

#### Multi-arm notification lifecycle and re-arm

Step (e)'s state-gated, fire-exactly-once clear is defined for a **single** detached call: one `build-busy` set, one wake, one clear. The finalize-barrier consumer detaches **three** independent arms ({CI, review, sonar}) that wake and settle at different times, and can re-detach a subset of them after a `re_settle` decision — so the single-flag gate generalizes to a **per-arm lifecycle** layered on top of the one shared title-token. Each arm moves through:

```text
pending → armed → notified → advanced
                       ↑          │
                       └─re-armed─┘   (re_settle names this arm `affected`)
```

- **`pending`** — the arm has not yet been detached (barrier not yet entered, or awaiting its turn if entry is staggered).
- **`armed`** — the arm's underlying wait is detached (step c) against the current `settled_head`: the CI arm's `ci wait`, the review arm's bot-comment poll, or the sonar arm's CE wait, each on its own existing ratchet.
- **`notified`** — the arm's wait returned a terminal state (`settled` or `failed`) and a wake fired for it (or for a sibling arm — see below). The arm is *notified*, not yet *advanced*: `compute_barrier_state` is pure and stateless, so it re-derives `proceed`/`pending`/`failed`/`affected` from the live signal snapshot on every call and will keep reporting an already-terminal arm in `proceed` on every subsequent wake, regardless of whether the orchestrator already acted on it.
- **`advanced`** — the orchestrator has processed this arm's notification exactly once (logged it, treated its result as final) and will not reprocess it on a later wake. Because the barrier state machine itself carries no such memory, the orchestrator holds the per-arm idempotency gate that step (e) held via the single `build-busy` flag: a conversation-scoped `advanced_arms` set, empty at barrier entry, that gains a name the first time that arm appears in `proceed` (or `failed`, for a terminal failure routed to triage) and is checked before acting on it again. A later wake whose `proceed`/`failed` bucket repeats an already-`advanced` name is a no-op for that name — mirroring step (e)'s "state already cleared → already handled" branch, applied per-arm instead of per-flag.

**Re-arm.** A `barrier_status: re_settle` decision's `affected` list names arms that were previously `advanced` but whose terminal observation is now stale (`head != settled_head` — a bounded-re-settle push moved HEAD after they settled). Re-arming an affected arm means: remove its name from `advanced_arms` (it is no longer considered handled) and re-detach it (step c again) against the **new** `settled_head` — i.e. drive it back from `advanced` to `armed`. Arms absent from `affected` keep their `advanced_arms` membership untouched and are NOT re-detached; this is what bounds the re-settle to the affected arms only, never a full barrier restart.

**Shared title-token spans the whole multi-wake window.** Unlike the single-call case, the `build-busy` token set in step (b) is NOT cleared on the barrier's first wake — it stays set across every intermediate `waiting` / `re_settle` decision, because the detached window is still open while any arm is `pending`, `armed`, or freshly `re-armed`. Step (e)'s clear condition generalizes from "the flag is present" to "the barrier's `barrier_status` is a terminal one (`complete` or `failed`) AND no arm is currently `armed`/`re-armed`" — read `title_token` on each wake exactly as step (e) does, but branch the clear on the barrier decision, not on the flag's mere presence: a `waiting` or `re_settle` status leaves the token untouched (more arms remain outstanding); only `complete` (all arms `advanced`, none `affected`) or `failed` (a genuine terminal failure, not a re-settle candidate) triggers the clear-and-push in step (e).

## Parameters

| Parameter | Description |
|-----------|-------------|
| `plan_id` | Plan identifier — forwarded to every `manage-locks` / `manage-status` / `platform-runtime` call below. |
| `consumer` | `build`, `ci-wait`, or `finalize-barrier` — selects the build-queue-slot rung (build only) and the completion-TOON shape. `finalize-barrier` follows the same no-build-slot rungs as `ci-wait` but wakes per-signal (see § "Finalize-wait barrier consumer specifics"). |
| `command` | The resolved wrapper `executable` (build consumer) or the CI-wait handler invocation (ci-wait consumer) to run detached. |
| `bash_timeout_seconds` | The architecture-resolved timeout, used ONLY on the fallback synchronous path (step 7). |

## Recipe

The seam is a fixed sequence. Steps (a) and (f) apply to the **build** consumer only; the remote-CI wait consumes no local build slot and skips them.

### (a) Acquire the build-queue slot (build consumer only)

Admit a build slot before detaching the wrapper, so the orchestrator honours the bounded-concurrency limiter (it enqueues FIFO when at capacity):

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue acquire \
  --plan-id {plan_id}
```

Capture the returned admission `id` for the matching release in step (f). The `ci-wait` consumer skips this step.

### (b) Set and live-push the `build-busy` title-token

Persist the `build-busy` state AND live-push the 🔨 glyph to the terminal so the title surfaces the build symbol for the whole detached window. Both calls are **best-effort** — a failure never aborts the detached call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status title-token set \
  --state build-busy --plan-id {plan_id}
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --plan-id {plan_id} --icon 🔨
```

The live `/dev/tty` OSC write is the only mechanism that repaints the terminal during a blocking/detached window — the bare `title-token set` alone writes `status.json` and is invisible until the next repaint. See [`persona-plan-marshall-agent` § build-busy bracketing](../../persona-plan-marshall-agent/SKILL.md#hard-rules-never-override) for the shared title-surface seam contract.

### (c) Invoke the command detached (background primitive)

Run the resolved wrapper command (build consumer) or the CI-wait handler (ci-wait consumer) with the Claude background primitive — the Bash `run_in_background: true` parameter — so the orchestrator does NOT block on it:

```text
Bash(command="{command}", run_in_background: true)
```

Do NOT poll for completion and do NOT `sleep`/`wait` on the backgrounded job — the completion notification is the wake signal (step d).

**Ledger stamping is automatic (no separate step here).** The detached wrapper `{command}` is itself a `python3 .plan/execute-script.py …` build-class invocation, so it traverses the executor dispatch boundary exactly as an inline `per_task` build does — and the boundary's tier-agnostic `kind=build` writer stamps the change-ledger with `worktree_sha` + `exit_code` (the detached orchestrator build carries `plan_id: null`). This seam therefore performs **no separate stamping step**; see [`../../manage-change-ledger/SKILL.md`](../../manage-change-ledger/SKILL.md) for the `run_in_background`-agnostic freshness stamp.

### (d) On the completion notification, read the compact TOON

When the background-completion notification arrives, read the wrapper's **compact result TOON** (its `status` / `errors[]` summary) — NEVER the raw build log. The compact TOON is the contract surface; the raw log is consulted only when the TOON's `log_file` pointer is needed for a specific failure investigation.

For the `build` consumer, analyse `status` (`success` / `error` / `timeout`) and the `errors[N]{file,line,message,category}` rows. For the `ci-wait` consumer, read `final_status`, `duration_sec`, and `failing_checks` from the handler's return TOON.

### (e) State-gated, fire-exactly-once clear

The persisted `build-busy` title-token state IS the **"not-yet-handled" gate**. The orchestrator reads the current state, and the gate — not the arrival of a reminder — decides whether to act:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Read `title_token` from the returned TOON, then branch:

- **`title_token == build-busy` (state present → not yet handled)** — this is the first handling of the completion. Do the work exactly once: consume the compact TOON (step d), clear the state, and push the restored repaint:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status title-token clear \
    --plan-id {plan_id}
  python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
    --plan-id {plan_id}
  ```

  The plain `session push-title-token` (no `--icon`) repaints to the current process icon (e.g. ➤ active).

- **`title_token` absent (state already cleared → already handled)** — this is a **repeated "still running" reminder**, not a fresh completion. **No-op**: do NOT re-read the TOON, do NOT re-clear, do NOT re-release the slot. An un-gated reminder that re-runs the handling on every repeat is the failure mode behind Claude Code issue #11190, where a leaked reminder re-fired thousands of tokens. The title-token-state gate is the idempotency mechanism that makes the clear fire exactly once regardless of how many reminders arrive.

All four title-surface operations (set / clear / both pushes) are **best-effort**, mirroring `merge_lock` — a failure of any one never aborts the wrapped operation.

### (f) Release the build-queue slot (build consumer only)

After the fire-exactly-once handling, release the admitted slot so the FIFO-oldest waiting build is promoted:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:build_queue release \
  --plan-id {plan_id} --id {admission_id}
```

The `ci-wait` consumer skips this step. The release fires only on the state-present branch of step (e) — a repeated reminder must not double-release.

### (g) Fallback — synchronous blocking call

When the Claude background primitive is unavailable (a non-Claude runtime, or the `run_in_background` parameter is not honoured), the seam degrades to **today's synchronous blocking call**: run `{command}` **inline** at `timeout: bash_timeout_seconds * 1000` (the architecture-resolved envelope's `bash_timeout_seconds`), still bracketed by the build-busy set (step b) and the clear (step e). On the synchronous path the completion is the Bash call's own return, so the clear is unconditional (there is no reminder to gate against) — but keeping the state-read gate is harmless and preserves one code path. The build-queue acquire/release (steps a, f) still apply for the build consumer.

The synchronous fallback is behaviourally identical to the pre-detach model; it exists so the Claude-specific wake primitive stays contained behind this seam rather than leaking a runtime branch into either consumer.

## Related

- [`persona-plan-marshall-agent` SKILL.md](../../persona-plan-marshall-agent/SKILL.md) — the build-busy bracketing contract that routes orchestrator-tier long-running calls through this seam (cross-reference, not duplication) and owns the shared title-surface seam semantics.
- [`phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md) — the `execution_tier=orchestrator` bullet names this seam as the canonical orchestrator-tier consumer (background-and-notify), preserving the "not run inline by the step body" invariant.
- [`tools-integration-ci/standards/blocking-wait-pattern.md`](../../tools-integration-ci/standards/blocking-wait-pattern.md) — the remote-CI wait's seed-then-watch pattern; the orchestrator detaches the whole CI wait behind this seam.
- [`manage-locks` SKILL.md](../../manage-locks/SKILL.md) — the build-queue `acquire` / `release` slot verbs.

## Output

Orchestration-guidance seam followed by the main-context orchestrator. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<detached {consumer} completed: {short outcome}>"
```

The orchestrator emits this shape when the seam is wrapped in a `Task: execution-context-{level}` dispatch. When followed inline in the main context, the detach/wake/clear transitions are surfaced via `manage-logging` records and the live `/dev/tty` title repaints.
