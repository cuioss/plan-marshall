# Plan-Server — the Orchestrator epic

**START HERE.** This roadmap owns one thesis:

> **plan-marshall must stop asking the Claude Code session to own expensive, long-running work.**
> Builds and test runs move out of the agent's process and into a machine-level owner — the
> session submits a job and later reads a result; it never *holds* the work. (CI waits stay on
> the bounded `ci:wait` primitives — they fail the scope criterion; see Rung 2.)

Split out of [`../plan-optimization/`](../plan-optimization/) on 2026-07-15. That roadmap's
cost-driver work is complete; this is a distinct surface with a distinct thesis. All backward-looking
material — why this epic exists, the kill forensics, the falsified hypotheses, the daemonization
experiment — lives in **one evidence document:
[`background-build-kill-forensics.md`](background-build-kill-forensics.md)**. This file and the
plan docs are goal-facing only.

## Goals

1. **Work-preservation.** A build must survive the loss of whatever is waiting on it. The harness
   reaps `run_in_background` jobs (proven — see evidence doc); the design consequence is that the
   *wait* and the *work* must be separate processes, so losing the wait is a hiccup, not a
   destroyed build.
2. **Cross-project coordination.** One machine-level owner for heavy work across all projects and
   worktrees, replacing N uncoordinated per-repo build queues (today: 3 projects × `max_slots=5` =
   up to 15 concurrent heavy builds, nothing coordinating them). **Concrete symptom this closes —
   lesson `2026-07-16-16-003`:** a build that runs in ~57s was killed at its 120s adaptive
   `subprocess.run` timeout because 3-project parallel contention stretched its wall-clock past 120s
   (a genuine timeout, distinct from the harness reap). **A good marshalld acceptance test: this
   timeout stops firing under 3-project parallel load.** Note this does NOT close two residual
   timeout-logic bugs (within-project variance vs a 1.25×-margin learned timeout; `--timeout` not a
   real override) — marshalld removes the contention variance source, not the fragile timeout logic.
3. **Legibility — a HARD requirement, and it must live in the poll response itself.** A killed or
   lost job must be unambiguous **at the call site**: the response an agent reads must distinguish
   job-died / job-running / job-done. A ledger `status` field alone does NOT satisfy this — agents
   demonstrably normalize the kill signature as "flaky environment" and blind-retry without ever
   consulting or escalating (evidence: forensics doc § "The failure is NORMALIZED as 'flaky
   environment'" — a landing report filed 23 days / 90 events of reaps as *"transient; retrying
   resolved them every time"*, which is survivorship framing: the retry works because victim
   selection is indiscriminate, not because a condition cleared). The ledger record is still
   required (metrics, retrospectives), but the call-site response is the primary surface.

## Design ground rules (settled — do not re-litigate)

- **No dormancy.** There is no inbound channel into a stopped Claude session (verified against
  docs/SDK/hooks/MCP: hooks cannot re-invoke the model, MCP has no honored server→client push, SDK
  `query(resume=id)` and `claude --resume -p` block the caller). The session stays live and polls.
  Any design whose value rests on "the session stops and gets woken" is invalid.
- **The wait must be a bounded FOREGROUND call.** `run_in_background: true` is the one invariant
  across all observed kills; foreground bounded calls are safe. The polling loop (see call model in
  [`plans/plan-server-core.md`](plans/plan-server-core.md)) uses foreground long-polls capped at
  **5 minutes** per call.
- **The server must be launched via full double-fork daemonization** (intermediate exits → daemon
  re-parents to PID 1). Plain `setsid`/`start_new_session` detachment does NOT survive the reaper;
  a PID-1-parented daemon does. Proven by experiment — evidence doc § "The setsid / daemonization
  experiment".
- **Strictly optional — registration is the single enable signal.** The server is an opt-in
  infrastructure feature ([[feedback_infra_steps_must_be_opt_in]]); a project uses it iff the
  operator registered it via the `manage-build-server` control skill (no config knob anywhere;
  nothing git-tracked). Unregistered = zero behavior change, no probe, no process. Registered =
  init-phase preflight (one script call, every outcome console-lined + decision-logged) with an
  operator ask before any auto-start.
- **Justify on work-preservation + coordination, never token savings.** Idle wall-clock is not
  token cost; an idling session is nearly free. **And do NOT expect marshalld to fix finalize
  cost** — the dominant finalize idle is ceremony (merge-queue waits, operator parking, review
  round-trips), a different problem with a different owner; a work-owning server would not have
  moved it. If a Rung 2 outline starts claiming finalize-idle savings, that is the smell that it
  has drifted off-thesis.
- **Do not reduce parallelism as a mitigation.** Concurrency is falsified as the kill trigger
  (evidence doc); throughput stays a top priority.

## Naming & scope name

Working name: **`marshalld`** — the plan-marshall **build server** (process name, log prefix).
Client contract lives in a tiny skill, working name `plan-marshall:build-server-client`; the
control surface (install/upgrade/start/stop/drain/status/register/unregister) lives in a dedicated
skill, working name `plan-marshall:manage-build-server` — deliberately NOT `marshall-steward`,
which is already too big (steward gets a pointer only). Names provisional until the Rung 2
outline confirms; recorded alternatives: `pm-server`, `workd`, and the original operator term
`async-server` — **retired as the concept name on 2026-07-16** when scope narrowed to build-class
work (CI waits stay on the bounded `ci:wait` primitives; see the scope criterion in
[`plans/plan-server-core.md`](plans/plan-server-core.md)). There is **no config knob**:
per-project registration via the control skill is the single enable signal, and nothing
build-server-related is git-tracked.

## The rungs

| Rung | What | State |
|---|---|---|
| **Rung 1** | Machine-global home (`~/.plan-marshall/`) + relocate machine-scoped state. No new process. | **✅ SHIPPED — PR #923 (2026-07-17).** All 6 deliverables: `home_root()` third anchor tier, credentials move + lazy race-safe migration, deny-rules single-sourced, `holder_is_dead` project-qualified, `build-queue.json` machine-global with `project_root` stamping, ADR-008. Archived: `.plan/local/archived-plans/2026-07-17-plan-global-home-root/`. |
| **Rung 2** | `marshalld` — the build server that OWNS build-class work (builds + test runs; CI waits deliberately excluded — scope criterion in the plan doc). | **✅ SHIPPED — PR #933 (2026-07-18, squash-merged).** All 11 deliverables: wire protocol/registry/schema, marshalld daemon core (double-fork to PID 1, asyncio Unix socket, verifier/scheduler/supervisor/journal), `manage-build-server` control skill, `build-server-client` skill + change-ledger `kind=job` persistence, build-execute routing on ONE machine-global queue file (`build_queue.py` refactored to shared reader/writer — operator decision, neither retired nor kept as separate limiter), await-long-running pointer, phase-1-init preflight, README/installation WSL2 docs, `doc/concepts/build-server.adoc`, `doc/developer/build-architecture.adoc`, acceptance suite (all 11 § Acceptance items). Finalize security-audit caught + fixed a real **S2 cwd-escape** (verifier now containment-verifies `project_path`, not just `exec_path`). Names CONFIRMED (no rename): `marshalld` / `build-server-client` / `manage-build-server`. Archived: `.plan/local/archived-plans/2026-07-18-plan-server-core/`. Lesson `2026-07-18-17-001` (verify EVERY client-settable execution path field). |
| **Rung 3** | Push-wake / central CI-ETA hub | Not scoped. Bounded by the no-dormancy rule above; any CI-side tenant must re-pass Rung 2's scope criterion. |

## Ordering

```
plan-background-build-kill  ── ✅ SHIPPED PR #912 (2026-07-16) ──

Rung 1 (plan-global-home-root)  ── ✅ SHIPPED PR #923 (2026-07-17) ──

Rung 2 (marshalld)  ── ✅ SHIPPED PR #933 (2026-07-18) ──  EPIC COMPLETE (Rung 3 not scoped)
```

**BK shipped (PR #912; archived at `../local/archived-plans/2026-07-16-background-build-kill/`).**
Goal 3 (legibility) is delivered: every `kind=build` ledger row carries a truthful `status`
(`success|error|timeout|killed`, nonzero exit authoritative), the freshness gate requires
`status=='success'` fail-closed, `manage-change-ledger classify-outcome` renders *"externally killed
— not flaky, do not blind-retry"* at the call site (`--worktree-sha` required), and the
`await-long-running` seam is kill-aware (state-gate first on wake, classify build-consumer-only,
`run_in_background` documented known-lossy). Self-validated live: the plan's own detached
module-tests was harness-killed mid-finalize and the new classifier caught it on its first call.
**Its outline DEFERRED deliverable 6 (the `plan_id=null` build-queue bypass) as CERTAIN_EXCLUDE**;
ownership passed to Rung 1, whose #923 rewrote the queue surface (admission ids are now
`{plan_id}:{uuid4}`, `holder_is_dead` project-qualified via per-entry `project_root`; the old
`_build_queue_slot.py` no longer exists). **Whether the null-plan_id bypass is fully closed in the
rewritten `build_queue.py` is unverified — re-check at Rung 2's outline**, since marshalld's queue
sits on this surface. The upstream bug report was DROPPED by operator decision (forensics evidence
stays internal). **Rung 1 shipped 2026-07-17 (PR #923); Rung 2 is startable now.**

## Directory layout & convention

Inherits [`../../../plan-optimization/00-README.md`](../../../plan-optimization/00-README.md)'s conventions:

**One plan document = one command.** `/plan-marshall task="implement .plan/local/orchestrator/plan-server/plans/<doc>.md"`

**Lifecycle (plan docs are handled like lesson sources):** `plans/` holds only not-yet-started work.
At plan creation the doc moves into the plan's own directory and is archived with the plan. After
archiving, update this README (each doc carries its exact steps in its "Lifecycle" footer).
`plans/` empty = epic complete.

| Location | Contents |
|---|---|
| [`background-build-kill-forensics.md`](background-build-kill-forensics.md) | **The single evidence document.** Kill forensics, falsified hypotheses, upstream corroboration, the daemonization experiment. Read before scoping anything here. |
| [`forensics-scripts/`](forensics-scripts/) | The five scripts that produced the forensics. Re-runnable against `~/.claude/projects/*/**.jsonl`; the corpus grows, so a re-run covers a wider window than the report. |
| [`plans/plan-server-core.md`](plans/plan-server-core.md) | **Rung 2.** `marshalld` build server — scope criterion, optionality model, call model, client skill, technology choice, security model (S1–S9), lifecycle/ops. **Startable now** (Rung 1 shipped). |
| [`architecture.md`](architecture.md) | **Interaction architecture for Rung 2 — operator-reviewed 2026-07-16, ready to implement** (component map, flows F1–F8, job state machine, deliberate absences). Companion to the plan doc; implementation input. |

## Known landmines (recorded so they aren't rediscovered)

1. **Deny-rule staleness is a SECURITY REGRESSION, not cosmetic.** `_cred_ensure_denied.py:22-34`
   hardcodes 13 deny-rule strings already written into users' host settings. Move the credentials
   dir without rewriting them and the rules keep naming the old path while secrets live at the new
   one — the guard silently stops guarding.
2. **`holder_is_dead` is not project-qualified.** `_locks_core.holder_is_dead` checks whether the
   holder's plan dir exists under the CALLING project's checkout — so under a shared global lock
   root, a foreign project's **live** lock would be misjudged dead and **falsely reclaimed
   mid-build**. Must be project-qualified before any machine-global anchor ships.
3. **Not all main-anchored state should move.** The bounded set is five: `merge.lock`,
   `run-configuration.json`, `lessons-learned`, `build-queue.json`, `merge-queue.json`
   (`marketplace_paths.py:363-372`), documented as *"Stays main-shared (never moves)"*
   (`cwd-policy.md:41,64`). **`build-queue.json` should go machine-global (CPU is a machine
   resource); `merge.lock`/`merge-queue.json` must NOT** — merging repo A doesn't conflict with repo
   B, and globalizing them would serialize unrelated repos. This renegotiates a documented invariant
   — an outline-gate decision, not an assumption.
4. **`get_project_name()` falls back to `Path.cwd().name`** (`_providers_core.py:157-183`) when no
   `version-control` provider URL is set — so the same project can hold credentials under different
   subdir names depending on where it was configured. A migration cannot assume a clean mapping.
5. **No migration machinery exists.** `upgrade.py:59-70`'s four stages (`regenerate-targets`,
   `reconcile-config`, `verify`, `land`) are artifact/config work — **none is a data-migration
   stage**. Relocating home-level state needs new machinery.
6. **`~/.plan-marshall-credentials` is already a DIRECTORY** (0700, one JSON per provider) — a
   dir→dir move, not a file→dir promotion. Only ~1 production line resolves it
   (`_providers_core.py:34`, a module-level constant read at import).

## Inherited open defects (routed from plan-optimization §5, 2026-07-17)

Two worktree-context-resolution bugs surfaced on the credentials / change-ledger surface this epic
owns. They were handed here (rather than left as orphans in the token-optimization queue). **⚠ Rung 1
SHIPPED (#923) WITHOUT fixing either — it relocated the credentials dir + `build-queue.json` (the
*surface* these bugs live on) but not these specific defects.** They are now **Rung-1-follow-up items,
to be verified against the NEW `~/.plan-marshall/` home-root layout** and folded into either a small
Rung-1 follow-up or the Rung 2 outline. Both have single-datapoint evidence; verify against current
source before implementing.

1. **`build-maven` `kind=build` ledger auto-append silently NO-OPs in a worktree** (evidence: nifi
   #454, 2026-07-17 — the consumer had to append the `kind=build` ledger row **manually three times**
   during F10 because the auto-append did nothing in a worktree context). **Why it matters here:**
   same surface as BK #912 — the truthful-`status` stamping, `classify-outcome`, and fail-closed
   freshness gate all READ the `kind=build` ledger. If the auto-append no-ops in worktrees, that
   machinery may be operating on an incomplete ledger: a killed/failed build might leave no row (which
   `classify-outcome` treats as `externally_killed`), but a **silently-dropped success append** is a
   different, unverified failure mode. **Owner: Rung-1 follow-up** (same worktree-CWD-vs-git-common-dir
   resolution root as landmine #2/#3 and the machine-global `build-queue.json` move) — verify the
   change-ledger append path's path resolution when it lands. Cross-repo lesson-store note: this
   plan-marshall-owned bug was filed into nifi's lesson store (5th recurrence of that trap) — re-home
   owed under a fresh native ID (never port by ID); the structural guard shipped as P6 #921 D3.

2. **Credentials resolution runs `credentials list --scope all` — over-broad enumeration** (evidence:
   TokenSheriff #577, 2026-07-17 — a sub-agent enumerated all scopes while resolving only the
   SonarCloud provider token; the security monitor flagged it. NOT exfiltration; nothing transmitted).
   The resolution path should scope to the specific provider, not enumerate everything. **Why it
   matters here:** directly on Rung 1's credentials-dir move surface and Rung 2's S4 security model
   ("secrets never cross the socket / job-env; daemon logs the sibling-of-credentials subtree"). A
   narrower default enumeration is cheaper to establish before the cred dir relocates than after.
   **Owner: Rung-1 follow-up** (cred surface, now relocated) with an S4 cross-check at the Rung 2 outline.

## Cross-links into plan-optimization

- [`../plan-optimization/plans/plan-terminal-title-stale-build-busy.md`](../plan-optimization/plans/plan-terminal-title-stale-build-busy.md)
  (**TT**) — downstream symptom; its only confirmed dangling `build-busy` path was the harness kill.
  **BK shipped #912 with a state-gate-first wake path (the clear now precedes classification), so
  TT's scope may be dissolved — re-verify at its outline before implementing.** **Stays in
  plan-optimization**; cross-linked both ways.
- **`marshall-orchestrator` skill** (staged `.plan/temp/marshall-orchestrator-plan.md`) — adjacent
  and NOT absorbed here: it is a resumable *epic-orchestration skill above plan-marshall*, a
  planning-layer concern. This epic is an *execution-layer process owner*. Different surface, similar
  word. Revisit only if they collide.
